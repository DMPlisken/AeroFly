import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import type { Aerodrome } from "./aerodromes";

const listAerodromesMock = vi.fn();

vi.mock("./client", async () => {
  const actual = await vi.importActual<typeof import("./client")>("./client");
  return {
    ...actual,
    apiListJson: (...args: unknown[]) => listAerodromesMock(...args),
  };
});

const { fetchAerodromeByIcao } = await import("./aerodromes");

function aerodrome(icao: string, overrides: Partial<Aerodrome> = {}): Aerodrome {
  return {
    icao,
    iata: null,
    name: icao,
    name_de: null,
    city: null,
    city_de: null,
    region: null,
    region_de: null,
    country: "DE",
    type: "international",
    latitude: null,
    longitude: null,
    elevation_ft: null,
    source_airac_cycle: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

beforeEach(() => {
  listAerodromesMock.mockReset();
});

afterEach(() => {
  listAerodromesMock.mockReset();
});

describe("fetchAerodromeByIcao", () => {
  it("normalizes input to uppercase before querying", async () => {
    listAerodromesMock.mockResolvedValue({ items: [aerodrome("EDDF")], total: 1 });

    await fetchAerodromeByIcao("eddf");

    expect(listAerodromesMock).toHaveBeenCalledWith(
      "/aerodromes",
      expect.objectContaining({ q: "EDDF", limit: 5 }),
    );
  });

  it("returns the exact ICAO match when the endpoint returns prefix hits", async () => {
    listAerodromesMock.mockResolvedValue({
      items: [aerodrome("EDDF"), aerodrome("EDDFM")],
      total: 2,
    });

    const result = await fetchAerodromeByIcao("EDDF");

    expect(result?.icao).toBe("EDDF");
  });

  it("returns null when no exact match is in the prefix response", async () => {
    listAerodromesMock.mockResolvedValue({
      items: [aerodrome("EDDFA"), aerodrome("EDDFB")],
      total: 2,
    });

    const result = await fetchAerodromeByIcao("EDDF");

    expect(result).toBeNull();
  });

  it("returns null on network error instead of throwing", async () => {
    listAerodromesMock.mockRejectedValue(new Error("network"));

    const result = await fetchAerodromeByIcao("EDDF");

    expect(result).toBeNull();
  });
});
