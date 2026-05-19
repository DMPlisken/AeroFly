import { useCallback, useEffect, useRef, useState } from "react";

import {
  getLatestBulk,
  startBulkSync,
  type ExtractionJob,
} from "@/api/extraction";
import { useI18n } from "@/i18n";

interface Props {
  /** ICAOs to sync — typically the user's favorites. */
  icaos: string[];
  /** Optional className for the wrapping container. */
  className?: string;
}

const POLL_INTERVAL_MS = 5000;

interface BulkProgress {
  total: number;
  completed: number;
  failed: number;
  runningIcao: string | null;
}

function summarise(
  expected: string[],
  jobs: Record<string, ExtractionJob | null>,
): BulkProgress {
  let completed = 0;
  let failed = 0;
  let runningIcao: string | null = null;
  for (const icao of expected) {
    const job = jobs[icao];
    if (!job) continue;
    if (job.status === "completed") completed += 1;
    else if (job.status === "failed") failed += 1;
    else if (job.status === "running" && runningIcao === null) runningIcao = icao;
  }
  return { total: expected.length, completed, failed, runningIcao };
}

/**
 * Dashboard favorites widget header button. Triggers a sequential sync
 * for every favorite the user has and shows an inline progress indicator
 * while the bulk job runs.
 */
export function BulkSyncButton({ icaos, className }: Props) {
  const { t } = useI18n();
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState<BulkProgress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<number | null>(null);
  const trackedIcaosRef = useRef<string[]>([]);

  const stopPolling = useCallback(() => {
    if (timerRef.current !== null) {
      window.clearTimeout(timerRef.current);
      timerRef.current = null;
    }
  }, []);

  const poll = useCallback(async () => {
    const expected = trackedIcaosRef.current;
    if (expected.length === 0) {
      setRunning(false);
      return;
    }
    try {
      const jobs = await getLatestBulk(expected);
      const summary = summarise(expected, jobs);
      setProgress(summary);
      if (summary.completed + summary.failed >= summary.total) {
        setRunning(false);
        stopPolling();
      } else {
        timerRef.current = window.setTimeout(poll, POLL_INTERVAL_MS);
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setRunning(false);
      stopPolling();
    }
  }, [stopPolling]);

  useEffect(() => stopPolling, [stopPolling]);

  const onTrigger = useCallback(async () => {
    if (icaos.length === 0 || running) return;
    setError(null);
    setRunning(true);
    trackedIcaosRef.current = [...icaos];
    setProgress({
      total: icaos.length,
      completed: 0,
      failed: 0,
      runningIcao: null,
    });
    try {
      await startBulkSync(icaos);
      timerRef.current = window.setTimeout(poll, POLL_INTERVAL_MS);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setRunning(false);
    }
  }, [icaos, running, poll]);

  const disabled = icaos.length === 0 || running;
  const label = (() => {
    if (running && progress) {
      if (progress.runningIcao) {
        return t("favorites.bulkSync.running", {
          done: progress.completed,
          total: progress.total,
          icao: progress.runningIcao,
        });
      }
      return t("favorites.bulkSync.progress", {
        done: progress.completed,
        total: progress.total,
      });
    }
    if (!running && progress && progress.total > 0) {
      return t("favorites.bulkSync.done", {
        done: progress.completed,
        total: progress.total,
      });
    }
    return t("favorites.bulkSync.trigger");
  })();

  return (
    <div className={className} style={{ display: "inline-flex", alignItems: "center", gap: "var(--space-2)" }}>
      <button
        type="button"
        className="btn btn-ghost btn-sm"
        onClick={onTrigger}
        disabled={disabled}
        title={icaos.length === 0 ? t("favorites.bulkSync.disabled") : undefined}
        style={{ whiteSpace: "nowrap" }}
      >
        <i
          className={
            running ? "fa-solid fa-rotate fa-spin" : "fa-solid fa-arrows-rotate"
          }
          style={{ marginRight: "var(--space-2)" }}
          aria-hidden="true"
        />
        {label}
      </button>
      {error && (
        <span
          style={{
            fontSize: "var(--fs-xs)",
            color: "var(--color-danger, #ef4444)",
          }}
        >
          {error}
        </span>
      )}
    </div>
  );
}
