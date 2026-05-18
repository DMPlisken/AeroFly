import { useCallback, useEffect, useRef, useState } from "react";

import {
  getExtractionJob,
  getLatestExtraction,
  startSync,
  type ExtractionJob,
} from "@/api/extraction";

const POLL_INTERVAL_MS = 2000;

export interface UseExtractionJobResult {
  job: ExtractionJob | null;
  error: string | null;
  triggerExtraction: () => Promise<void>;
  isActive: boolean;
}

/**
 * Fetches the latest extraction job for an aerodrome and, if one is
 * queued/running, polls until it completes. Exposes a trigger to kick
 * off a new job on demand.
 */
export function useExtractionJob(
  icao: string,
  onComplete?: (job: ExtractionJob) => void,
): UseExtractionJobResult {
  const [job, setJob] = useState<ExtractionJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);
  const onCompleteRef = useRef(onComplete);

  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const stopPolling = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const pollOnce = useCallback(
    async (jobId: string) => {
      try {
        const fresh = await getExtractionJob(jobId);
        setJob(fresh);
        if (fresh.status === "completed") {
          onCompleteRef.current?.(fresh);
          stopPolling();
        } else if (fresh.status === "failed") {
          stopPolling();
        } else {
          timerRef.current = window.setTimeout(() => pollOnce(jobId), POLL_INTERVAL_MS);
        }
      } catch (e) {
        setError(e instanceof Error ? e.message : String(e));
        stopPolling();
      }
    },
    [stopPolling],
  );

  // Resume polling if a job is already in flight when we land on the page.
  useEffect(() => {
    if (!icao) return;
    let cancelled = false;
    getLatestExtraction(icao)
      .then((latest) => {
        if (cancelled) return;
        if (latest) {
          setJob(latest);
          if (latest.status === "queued" || latest.status === "running") {
            timerRef.current = window.setTimeout(
              () => pollOnce(latest.id),
              POLL_INTERVAL_MS,
            );
          }
        }
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e));
      });
    return () => {
      cancelled = true;
      stopPolling();
    };
  }, [icao, pollOnce, stopPolling]);

  const triggerExtraction = useCallback(async () => {
    if (!icao) return;
    setError(null);
    stopPolling();
    try {
      // Full sync: scrape DFS → import manifest → extract structured fields.
      // The legacy /extract endpoint (charts-only re-extract) is still
      // available via startExtraction but the UI button now always goes
      // through the full pipeline so the user gets fresh chart material
      // automatically.
      const fresh = await startSync(icao);
      setJob(fresh);
      timerRef.current = window.setTimeout(() => pollOnce(fresh.id), POLL_INTERVAL_MS);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  }, [icao, pollOnce, stopPolling]);

  const isActive = job?.status === "queued" || job?.status === "running";

  return { job, error, triggerExtraction, isActive };
}
