import { apiGetJson, apiPostJson } from "./client";

export type ExtractionStatus = "queued" | "running" | "completed" | "failed";

export interface ExtractionJob {
  id: string;
  aerodrome_icao: string;
  status: ExtractionStatus;
  progress_pct: number;
  current_step: string | null;
  fields_written: number;
  field_groups_completed: Record<string, unknown>;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  error: string | null;
}

export function startExtraction(icao: string): Promise<ExtractionJob> {
  return apiPostJson<ExtractionJob>(`/aerodromes/${icao}/extract`);
}

/**
 * Full per-aerodrome sync: scrape → import → extract. Returns the same
 * ExtractionJob shape as `startExtraction`; the UI polls it identically.
 */
export function startSync(icao: string): Promise<ExtractionJob> {
  return apiPostJson<ExtractionJob>(`/aerodromes/${icao}/sync`);
}

export function getExtractionJob(jobId: string): Promise<ExtractionJob> {
  return apiGetJson<ExtractionJob>(`/extraction/jobs/${jobId}`);
}

export function getLatestExtraction(icao: string): Promise<ExtractionJob | null> {
  return apiGetJson<ExtractionJob | null>(`/aerodromes/${icao}/extraction/latest`);
}
