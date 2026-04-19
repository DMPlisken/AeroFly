import { useI18n } from "@/i18n";

/** Single-line reminder that rendered chart previews are not for operational use. */
export function ChartReferenceBanner({ airac }: { airac: string | null }) {
  const { t } = useI18n();
  return (
    <div className="chart-reference-banner" role="note">
      <i className="fa-solid fa-triangle-exclamation" aria-hidden="true" />
      <span>
        <strong>{t("chart.reference.only")}</strong>
        {airac ? (
          <>
            {" "}
            {t("chart.airac.label")}{" "}
            <span className="mono">{airac}</span>
          </>
        ) : null}
      </span>
    </div>
  );
}
