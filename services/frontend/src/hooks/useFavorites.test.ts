import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/api/favorites", () => ({
  listFavorites: vi.fn(),
  addFavorite: vi.fn(),
  removeFavorite: vi.fn(),
}));

import * as favoritesApi from "@/api/favorites";
import {
  __getFavoritesStateForTests,
  __resetFavoritesStoreForTests,
  loadFavorites,
  toggleFavorite,
} from "./useFavorites";

const { listFavorites, addFavorite, removeFavorite } = vi.mocked(favoritesApi);

beforeEach(() => {
  __resetFavoritesStoreForTests();
  listFavorites.mockReset();
  addFavorite.mockReset();
  removeFavorite.mockReset();
});

afterEach(() => {
  __resetFavoritesStoreForTests();
});

describe("loadFavorites", () => {
  it("populates the store on success", async () => {
    listFavorites.mockResolvedValue([
      { icao: "EDDF", created_at: "2026-05-16T10:00:00Z" },
      { icao: "EDDM", created_at: "2026-05-16T10:01:00Z" },
    ]);

    await loadFavorites();

    const state = __getFavoritesStateForTests();
    expect(state.loaded).toBe(true);
    expect(state.error).toBeNull();
    expect([...state.icaos]).toEqual(["EDDF", "EDDM"]);
  });

  it("captures the error message on failure", async () => {
    listFavorites.mockRejectedValue(new Error("500 boom"));

    await loadFavorites();

    const state = __getFavoritesStateForTests();
    expect(state.loaded).toBe(true);
    expect(state.error).toBe("500 boom");
    expect(state.icaos.size).toBe(0);
  });

  it("is idempotent — only fetches once across concurrent callers", async () => {
    listFavorites.mockResolvedValue([]);

    await Promise.all([loadFavorites(), loadFavorites(), loadFavorites()]);

    expect(listFavorites).toHaveBeenCalledTimes(1);
  });
});

describe("toggleFavorite — add", () => {
  beforeEach(() => {
    listFavorites.mockResolvedValue([]);
  });

  it("optimistically adds to the store before the API resolves", async () => {
    addFavorite.mockReturnValue(new Promise(() => {})); // never resolves
    await loadFavorites();

    void toggleFavorite("EDDF");

    expect(__getFavoritesStateForTests().icaos.has("EDDF")).toBe(true);
    expect(addFavorite).toHaveBeenCalledWith("EDDF");
  });

  it("normalizes lowercase ICAO to uppercase before storing", async () => {
    addFavorite.mockResolvedValue({ icao: "EDDF", created_at: "x" });
    await loadFavorites();

    await toggleFavorite("eddf");

    const state = __getFavoritesStateForTests();
    expect(state.icaos.has("EDDF")).toBe(true);
    expect(state.icaos.has("eddf")).toBe(false);
    expect(addFavorite).toHaveBeenCalledWith("EDDF");
  });

  it("rolls back and records the error if the API call fails", async () => {
    addFavorite.mockRejectedValue(new Error("503 down"));
    await loadFavorites();

    await toggleFavorite("EDDF");

    const state = __getFavoritesStateForTests();
    expect(state.icaos.has("EDDF")).toBe(false);
    expect(state.error).toBe("503 down");
  });

  it("ignores an empty/whitespace ICAO without calling the API", async () => {
    await loadFavorites();
    await toggleFavorite("   ");

    expect(addFavorite).not.toHaveBeenCalled();
    expect(__getFavoritesStateForTests().icaos.size).toBe(0);
  });
});

describe("toggleFavorite — remove", () => {
  beforeEach(async () => {
    listFavorites.mockResolvedValue([
      { icao: "EDDF", created_at: "2026-05-16T10:00:00Z" },
    ]);
    await loadFavorites();
  });

  it("optimistically removes from the store before the API resolves", () => {
    removeFavorite.mockReturnValue(new Promise(() => {}));

    void toggleFavorite("EDDF");

    expect(__getFavoritesStateForTests().icaos.has("EDDF")).toBe(false);
    expect(removeFavorite).toHaveBeenCalledWith("EDDF");
  });

  it("rolls back if the delete fails", async () => {
    removeFavorite.mockRejectedValue(new Error("418 teapot"));

    await toggleFavorite("EDDF");

    const state = __getFavoritesStateForTests();
    expect(state.icaos.has("EDDF")).toBe(true);
    expect(state.error).toBe("418 teapot");
  });
});
