import { useMemo, useRef, useState, type KeyboardEvent } from "react";

import type { Chart } from "@/api/aerodromes";
import { useI18n } from "@/i18n";
import type { TranslationKey } from "@/i18n/en";
import { groupChartsByType } from "@/utils/groupChartsByType";

import { ChartCard } from "./ChartCard";
import { ChartReferenceBanner } from "./ChartReferenceBanner";
import { ChartViewer } from "./ChartViewer";

interface Props {
  charts: Chart[];
  airac: string | null;
}

/**
 * Grouped thumbnail grid. Visually identifies each chart before the user
 * commits to opening it. Click / Enter / Space opens the fullscreen viewer;
 * arrow keys navigate spatially within the flat sequence of cards; focus
 * returns to the opened card when the viewer closes.
 */
export function ChartGrid({ charts, airac }: Props) {
  const { t } = useI18n();
  const groups = useMemo(() => groupChartsByType(charts), [charts]);
  const cardRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const [viewerChart, setViewerChart] = useState<Chart | null>(null);
  const [openedIndex, setOpenedIndex] = useState<number | null>(null);

  if (charts.length === 0) {
    return (
      <div className="chart-grid-empty">
        <i className="fa-solid fa-image" aria-hidden="true" />
        <p>{t("chart.grid.empty")}</p>
      </div>
    );
  }

  // Build a flat list of { chart, type, index } so arrow keys can step through
  // cards across group boundaries.
  const flat: Array<{ chart: Chart; type: ReturnType<typeof groupChartsByType>[number]["type"] }> = [];
  for (const group of groups) {
    for (const chart of group.charts) {
      flat.push({ chart, type: group.type });
    }
  }

  function handleOpen(index: number) {
    setOpenedIndex(index);
    setViewerChart(flat[index].chart);
  }

  function handleClose() {
    const i = openedIndex;
    setViewerChart(null);
    setOpenedIndex(null);
    // Restore focus to the card that opened the viewer (keyboard users).
    if (i !== null) {
      queueMicrotask(() => cardRefs.current[i]?.focus());
    }
  }

  function handleGridKeyDown(index: number) {
    return (event: KeyboardEvent<HTMLButtonElement>) => {
      let target: number | null = null;
      switch (event.key) {
        case "ArrowRight":
          target = Math.min(index + 1, flat.length - 1);
          break;
        case "ArrowLeft":
          target = Math.max(index - 1, 0);
          break;
        case "Home":
          target = 0;
          break;
        case "End":
          target = flat.length - 1;
          break;
        default:
          return;
      }
      event.preventDefault();
      cardRefs.current[target]?.focus();
    };
  }

  let cursor = 0;

  return (
    <>
      <ChartReferenceBanner airac={airac} />
      {groups.map((group) => (
        <section className="chart-group" key={group.type}>
          <header className="chart-group-head">
            <h3 className="chart-group-title">
              {t(`chart.group.${group.type}` as TranslationKey)}
            </h3>
            <span className="chart-group-count">
              {t("chart.card.groupCount", { n: group.charts.length })}
            </span>
          </header>
          <div className="chart-grid">
            {group.charts.map((chart) => {
              const index = cursor++;
              return (
                <ChartCard
                  key={chart.id}
                  chart={chart}
                  type={group.type}
                  airac={airac}
                  onOpen={() => handleOpen(index)}
                  onGridKeyDown={handleGridKeyDown(index)}
                  index={index}
                  ref={(el) => {
                    cardRefs.current[index] = el;
                  }}
                />
              );
            })}
          </div>
        </section>
      ))}
      {viewerChart && viewerChart.preview_url && (
        <ChartViewer
          title={viewerChart.title}
          previewUrl={viewerChart.preview_url}
          onClose={handleClose}
        />
      )}
    </>
  );
}
