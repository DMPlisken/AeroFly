import {
  forwardRef,
  useState,
  type ForwardedRef,
  type KeyboardEvent,
  type MouseEvent,
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
  onPrint?: () => void;
  selectMode?: boolean;
  selected?: boolean;
  onToggleSelect?: () => void;
}

type ImageState = "loading" | "ready" | "error";

export const ChartCard = forwardRef(function ChartCard(
  {
    chart,
    type,
    airac,
    onOpen,
    onGridKeyDown,
    index,
    onPrint,
    selectMode,
    selected,
    onToggleSelect,
  }: Props,
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
      if (selectMode) {
        onToggleSelect?.();
      } else {
        onOpen();
      }
      return;
    }
    onGridKeyDown?.(event);
  }

  function handleClick() {
    if (selectMode) {
      onToggleSelect?.();
    } else {
      onOpen();
    }
  }

  function handleOverlayClick(
    event: MouseEvent<HTMLElement>,
    action: (() => void) | undefined,
  ) {
    event.stopPropagation();
    event.preventDefault();
    action?.();
  }

  return (
    <button
      type="button"
      ref={ref}
      className={`chart-card chart-card--${type}${selected ? " is-selected" : ""}`}
      onClick={handleClick}
      onKeyDown={handleKeyDown}
      aria-label={`${badgeLabel}: ${title}`}
      aria-pressed={selectMode ? !!selected : undefined}
      data-chart-id={chart.id}
      data-chart-type={type}
      data-index={index}
    >
      <div className={`chart-card-thumb${state === "error" ? " is-empty" : ""}`}>
        {selectMode && (
          <span
            className="chart-card-overlay-select"
            role="checkbox"
            aria-checked={!!selected}
            aria-label={t("chart.print.aria.selectChart")}
            onClick={(e) => handleOverlayClick(e, onToggleSelect)}
          >
            {selected && <i className="fa-solid fa-check" aria-hidden="true" />}
          </span>
        )}
        {onPrint && (
          <span
            className="chart-card-overlay-print"
            role="button"
            tabIndex={0}
            aria-label={t("chart.print.aria.print")}
            title={t("chart.print.single")}
            onClick={(e) => handleOverlayClick(e, onPrint)}
            onKeyDown={(e) => {
              if (e.key === "Enter" || e.key === " ") {
                e.stopPropagation();
                e.preventDefault();
                onPrint();
              }
            }}
          >
            <i className="fa-solid fa-print" aria-hidden="true" />
          </span>
        )}
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
