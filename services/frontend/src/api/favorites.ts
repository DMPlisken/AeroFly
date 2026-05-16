/**
 * Favorites API client.
 *
 * Phase 1: no login. The browser generates a UUID v4 once and persists it
 * in localStorage under `aerofly.deviceId`. Every favorites request sends
 * it as the `X-Device-Id` header. The server treats the id as opaque
 * ownership — no user table, no cross-device sync.
 */

const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";

const DEVICE_ID_STORAGE_KEY = "aerofly.deviceId";

export interface Favorite {
  icao: string;
  created_at: string;
}

function randomDeviceId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  // Fallback for very old browsers / non-secure contexts.
  return "device-" + Math.random().toString(36).slice(2) + Date.now().toString(36);
}

export function getDeviceId(): string {
  try {
    const existing = window.localStorage.getItem(DEVICE_ID_STORAGE_KEY);
    if (existing) return existing;
    const fresh = randomDeviceId();
    window.localStorage.setItem(DEVICE_ID_STORAGE_KEY, fresh);
    return fresh;
  } catch {
    // localStorage unavailable (private mode, SSR) — return a per-session id.
    return randomDeviceId();
  }
}

function favoritesUrl(path = ""): string {
  return new URL(`${API_BASE}/favorites${path}`, window.location.origin).toString();
}

function headers(): HeadersInit {
  return {
    "X-Device-Id": getDeviceId(),
    "Content-Type": "application/json",
  };
}

export async function listFavorites(): Promise<Favorite[]> {
  const response = await fetch(favoritesUrl(), { headers: headers() });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return (await response.json()) as Favorite[];
}

export async function addFavorite(icao: string): Promise<Favorite> {
  const response = await fetch(favoritesUrl(), {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ icao }),
  });
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return (await response.json()) as Favorite;
}

export async function removeFavorite(icao: string): Promise<void> {
  const response = await fetch(favoritesUrl(`/${encodeURIComponent(icao)}`), {
    method: "DELETE",
    headers: headers(),
  });
  if (!response.ok && response.status !== 204) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
}
