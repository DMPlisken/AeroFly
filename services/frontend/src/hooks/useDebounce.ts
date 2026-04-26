import { useEffect, useState } from "react";

/**
 * Debounce a rapidly changing value (e.g. a search input). Returns the most
 * recent value that has been stable for at least `delayMs` milliseconds.
 */
export function useDebounce<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(handle);
  }, [value, delayMs]);
  return debounced;
}
