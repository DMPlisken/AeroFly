const API_BASE =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ?? "/api";

export interface ApiListResponse<T> {
  items: T[];
  total: number;
}

export async function apiListJson<T>(
  path: string,
  params?: Record<string, string | number | undefined>,
): Promise<ApiListResponse<T>> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  if (params) {
    for (const [k, v] of Object.entries(params)) {
      if (v !== undefined && v !== "") url.searchParams.set(k, String(v));
    }
  }
  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  const total = Number(response.headers.get("X-Total-Count") ?? 0);
  const items = (await response.json()) as T[];
  return { items, total };
}

export async function apiGetJson<T>(path: string): Promise<T> {
  const url = new URL(`${API_BASE}${path}`, window.location.origin);
  const response = await fetch(url.toString());
  if (!response.ok) {
    throw new Error(`${response.status} ${response.statusText}`);
  }
  return (await response.json()) as T;
}
