import {
  forwardRef,
  useState,
  type ForwardedRef,
  type KeyboardEvent,
} from "react";

import type { Chart } from "@/api/aerodromes";
import { useI18n } from "@/i18n";
import type { ChartGroupKey } from "@/utils/groupChartsByType";
import type { TranslationKey } from "@/i18n/en";

type GridKeyboardHandler = (event: KeyboardEvent<HTMLButtonElement>) => void;

interface Props {
  chart: Chart;
  type: ChartGroupKey;
  airac: string | null;
  onOpen: () => void;
  onGridKeyDown?: GridKeyboardHandler;
  index: number;
}

type ImageState = "loading" | "ready" | "error";

export const ChartCard = forwardRef(function ChartCard(
  { chart, type, airac, onOpen, onGridKeyDown, index }: Props,
  ref: ForwardedRef<HTMLButtonElement>,
) {
  const { t, locale } = useI18n();
  const [state, setState] = useState<ImageState>(
    chart.preview_url ? "loading" : "error",
  );
  const title = locale === "de" && chart.title_de ? chart.title_de : chart.title;
  const badgeLabel = t(`chart.badge.${type}` as TranslationKey);

  function handleKeyDown(event: KeyboardEvent<HTMLButtonElement>) {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      onOpen();
      return;
    }
    onGridKeyDown?.(event);
  }

  return (
    <button
      type="button"
      ref={ref}
      className={`chart-card chart-card--${type}`}
      onClick={onOpen}
      onKeyDown={handleKeyDown}
      aria-label={`${badgeLabel}: ${title}`}
      data-chart-id={chart.id}
      data-chart-type={type}
      data-index={index}
    >
      <div className={`chart-card-thumb${state === "error" ? " is-empty" : ""}`}>
        <span className={`chart-card-badge chart-card-badge--${type}`}>{badgeLabel}</span>
        {chart.preview_url && state !== "error" ? (
          <img
            src={chart.preview_url}
            alt=""
            loading="lazy"
            decoding="async"
            onLoad={() => setState("ready")}
            onError={() => setState("error")}
            className="chart-card-image"
            draggable={false}
          />
        ) : (
          <i
            className="fa-solid fa-image chart-card-placeholder"
            aria-hidden="true"
          />
        )}
        {state === "loading" && <span className="chart-card-skeleton" aria-hidden="true" />}
      </div>
      <div className="chart-card-body">
        <span className="chart-card-title" title={title}>
          {title}
        </span>
        <span className="chart-card-foot">
          <span>
            {airac ? `AIRAC ${airac}` : ""}
          </span>
          <span className="chart-card-status">
            {state === "error" ? t("chart.card.noPreview") : "PREVIEW"}
          </span>
        </span>
      </div>
    </button>
  );
});
