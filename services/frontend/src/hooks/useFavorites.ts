/**
 * Global favorites store + `useFavorites` hook.
 *
 * One source of truth shared across the app: every consumer (cards, detail
 * header, chart viewer toolbar, search tab) sees the same Set and reacts to
 * the same updates. Implemented with `useSyncExternalStore` so there is no
 * React Context / Provider wiring — components just import and use the hook.
 *
 * Toggles are optimistic: the UI updates immediately, the API call follows;
 * if it fails the local state is rolled back and the error is exposed.
 */

import { useCallback, useEffect, useSyncExternalStore } from "react";

import {
  addFavorite as addFavoriteApi,
  listFavorites,
  removeFavorite as removeFavoriteApi,
} from "@/api/favorites";

interface State {
  icaos: ReadonlySet<string>;
  loaded: boolean;
  loading: boolean;
  error: string | null;
}

let state: State = {
  icaos: new Set(),
  loaded: false,
  loading: false,
  error: null,
};

const listeners = new Set<() => void>();

function snapshot(): State {
  return state;
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function emit(): void {
  for (const listener of listeners) listener();
}

function setState(next: Partial<State>): void {
  state = { ...state, ...next };
  emit();
}

let initPromise: Promise<void> | null = null;

export async function loadFavorites(): Promise<void> {
  if (initPromise) return initPromise;
  initPromise = (async () => {
    setState({ loading: true, error: null });
    try {
      const list = await listFavorites();
      setState({
        icaos: new Set(list.map((f) => f.icao)),
        loaded: true,
        loading: false,
        error: null,
      });
    } catch (err) {
      setState({
        loaded: true,
        loading: false,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  })();
  return initPromise;
}

function normalize(icao: string): string {
  return icao.trim().toUpperCase();
}

export async function toggleFavorite(icao: string): Promise<void> {
  const code = normalize(icao);
  if (!code) return;
  const wasActive = state.icaos.has(code);

  // Optimistic update
  const next = new Set(state.icaos);
  if (wasActive) next.delete(code);
  else next.add(code);
  setState({ icaos: next, error: null });

  try {
    if (wasActive) await removeFavoriteApi(code);
    else await addFavoriteApi(code);
  } catch (err) {
    // Rollback
    const rolledBack = new Set(state.icaos);
    if (wasActive) rolledBack.add(code);
    else rolledBack.delete(code);
    setState({
      icaos: rolledBack,
      error: err instanceof Error ? err.message : String(err),
    });
  }
}

export interface UseFavoritesResult {
  /** All favorited ICAOs (normalized to uppercase). */
  favorites: ReadonlySet<string>;
  /** Convenience: number of favorites. */
  count: number;
  /** True after the initial fetch finished (success or failure). */
  loaded: boolean;
  /** True while the initial fetch is in flight. */
  loading: boolean;
  /** Last error from any operation (load or toggle), or null. */
  error: string | null;
  /** O(1) membership check. */
  isFavorite: (icao: string) => boolean;
  /** Toggle a favorite. Optimistic; rolls back on API failure. */
  toggle: (icao: string) => Promise<void>;
}

export function useFavorites(): UseFavoritesResult {
  const snap = useSyncExternalStore(subscribe, snapshot, snapshot);

  useEffect(() => {
    void loadFavorites();
  }, []);

  const isFavorite = useCallback(
    (icao: string) => snap.icaos.has(normalize(icao)),
    [snap.icaos],
  );

  return {
    favorites: snap.icaos,
    count: snap.icaos.size,
    loaded: snap.loaded,
    loading: snap.loading,
    error: snap.error,
    isFavorite,
    toggle: toggleFavorite,
  };
}

/** Read-only snapshot of the favorites store — for tests only. */
export function __getFavoritesStateForTests(): State {
  return state;
}

/**
 * Reset all internal state — for tests only.
 */
export function __resetFavoritesStoreForTests(): void {
  state = { icaos: new Set(), loaded: false, loading: false, error: null };
  initPromise = null;
  emit();
}
