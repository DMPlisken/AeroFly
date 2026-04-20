import { useI18n } from "@/i18n";
import type { ExtractionJob } from "@/api/extraction";

interface ExtractionPanelProps {
  icao: string;
  job: ExtractionJob | null;
  error: string | null;
  isActive: boolean;
  onTrigger: () => void;
}

/**
 * Header panel for the aerodrome detail page — kicks off extraction and
 * shows a progress bar while a job is running.
 *
 * The panel is always visible; when no job has run yet it just shows the
 * "Daten aktualisieren" CTA. During an active job it shows a bar +
 * current step. After completion it shows the written-field tally.
 */
export function ExtractionPanel({
  icao,
  job,
  error,
  isActive,
  onTrigger,
}: ExtractionPanelProps) {
  const { t } = useI18n();
  void icao;

  return (
    <div
      className="card"
      style={{
        padding: "var(--space-3) var(--space-4)",
        marginBottom: "var(--space-3)",
        display: "flex",
        alignItems: "center",
        gap: "var(--space-3)",
        flexWrap: "wrap",
      }}
    >
      <button
        type="button"
        className="btn btn-primary"
        onClick={onTrigger}
        disabled={isActive}
        style={{ whiteSpace: "nowrap" }}
      >
        <i
          className={
            isActive ? "fa-solid fa-rotate fa-spin" : "fa-solid fa-wand-magic-sparkles"
          }
          style={{ marginRight: "var(--space-2)" }}
        />
        {isActive ? t("extraction.running") : t("extraction.trigger")}
      </button>

      <div style={{ flex: 1, minWidth: 240 }}>
        {isActive && job ? (
          <>
            <div
              style={{
                height: 8,
                background: "var(--color-border)",
                borderRadius: 999,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${Math.max(2, job.progress_pct)}%`,
                  height: "100%",
                  background:
                    "linear-gradient(90deg, var(--color-primary), var(--color-accent, var(--color-primary)))",
                  transition: "width 400ms ease",
                }}
              />
            </div>
            <div
              style={{
                marginTop: 4,
                fontSize: "var(--fs-xs)",
                color: "var(--color-text-muted)",
              }}
            >
              {job.progress_pct}% — {job.current_step ?? t("extraction.working")}
            </div>
          </>
        ) : job?.status === "completed" ? (
          <div
            style={{
              fontSize: "var(--fs-xs)",
              color: "var(--color-text-muted)",
            }}
          >
            <i
              className="fa-solid fa-check"
              style={{ color: "var(--color-success, #10b981)", marginRight: 6 }}
            />
            {t("extraction.completed", {
              fields: job.fields_written,
              at: new Date(job.completed_at ?? job.created_at).toLocaleString(),
            })}
          </div>
        ) : job?.status === "failed" ? (
          <div
            style={{
              fontSize: "var(--fs-xs)",
              color: "var(--color-danger, #ef4444)",
            }}
          >
            <i className="fa-solid fa-triangle-exclamation" style={{ marginRight: 6 }} />
            {t("extraction.failed", {
              error: (job.error ?? "").slice(0, 160),
            })}
          </div>
        ) : error ? (
          <div
            style={{
              fontSize: "var(--fs-xs)",
              color: "var(--color-danger, #ef4444)",
            }}
          >
            {error}
          </div>
        ) : (
          <div
            style={{
              fontSize: "var(--fs-xs)",
              color: "var(--color-text-muted)",
            }}
          >
            {t("extraction.hint")}
          </div>
        )}
      </div>
    </div>
  );
}
