import { useCallback, useEffect, useMemo, useRef, useState, type KeyboardEvent } from "react";

import type { Chart, RotationDegrees } from "@/api/aerodromes";
import { useI18n } from "@/i18n";
import type { TranslationKey } from "@/i18n/en";
import { groupChartsByType } from "@/utils/groupChartsByType";
import {
  printChartViewSnapshot,
  printDocuments,
  type ChartViewSnapshot,
} from "@/utils/printDocuments";

import { ChartCard } from "./ChartCard";
import { ChartReferenceBanner } from "./ChartReferenceBanner";
import { ChartViewer } from "./ChartViewer";

interface Props {
  charts: Chart[];
  airac: string | null;
  /** ICAO of the parent aerodrome — used to persist per-chart rotation. */
  aerodromeIcao?: string;
  /** Localized name for the print header. */
  aerodromeName?: string;
}

/**
 * Grouped thumbnail grid. Visually identifies each chart before the user
 * commits to opening it. Click / Enter / Space opens the fullscreen viewer;
 * arrow keys navigate spatially within the flat sequence of cards; focus
 * returns to the opened card when the viewer closes.
 */
export function ChartGrid({ charts, airac, aerodromeIcao, aerodromeName }: Props) {
  const { t, locale } = useI18n();
  // Local mirror so a rotation persisted in the viewer is reflected on
  // re-opening the same chart, without waiting for a parent refetch.
  const [chartState, setChartState] = useState<Chart[]>(charts);
  useEffect(() => {
    setChartState(charts);
  }, [charts]);

  const groups = useMemo(() => groupChartsByType(chartState), [chartState]);
  const cardRefs = useRef<Array<HTMLButtonElement | null>>([]);
  const [viewerChart, setViewerChart] = useState<Chart | null>(null);
  const [openedIndex, setOpenedIndex] = useState<number | null>(null);
  const [selectMode, setSelectMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<number>>(new Set());

  const flat = useMemo(() => {
    const out: Array<{ chart: Chart; type: ReturnType<typeof groupChartsByType>[number]["type"] }> = [];
    for (const group of groups) {
      for (const chart of group.charts) {
        out.push({ chart, type: group.type });
      }
    }
    return out;
  }, [groups]);

  const chartTitle = useCallback(
    (chart: Chart) =>
      locale === "de" && chart.title_de ? chart.title_de : chart.title,
    [locale],
  );

  const buildPrintLabels = useCallback(
    () => ({
      printedAt: t("chart.print.header.printedAt"),
      page: t("chart.print.header.page"),
      typeLabel: (chartType: string) => {
        const key = `chart.group.${chartType}` as TranslationKey;
        return t(key);
      },
      chartTitle,
    }),
    [chartTitle, t],
  );

  const buildPrintCtx = useCallback(
    () =>
      aerodromeIcao
        ? {
            icao: aerodromeIcao,
            name: aerodromeName ?? aerodromeIcao,
            airac,
          }
        : null,
    [aerodromeIcao, aerodromeName, airac],
  );

  const print = useCallback(
    (toPrint: Chart[]) => {
      const ctx = buildPrintCtx();
      if (!ctx || toPrint.length === 0) return;
      void printDocuments(toPrint, ctx, buildPrintLabels());
    },
    [buildPrintCtx, buildPrintLabels],
  );

  const printView = useCallback(
    (snapshot: ChartViewSnapshot, chart: Chart) => {
      const ctx = buildPrintCtx();
      if (!ctx) return;
      void printChartViewSnapshot(
        snapshot,
        chart,
        ctx,
        buildPrintLabels(),
        t("chart.print.header.detailSuffix"),
      );
    },
    [buildPrintCtx, buildPrintLabels, t],
  );

  if (charts.length === 0) {
    return (
      <div className="chart-grid-empty">
        <i className="fa-solid fa-image" aria-hidden="true" />
        <p>{t("chart.grid.empty")}</p>
      </div>
    );
  }

  function handleOpen(index: number) {
    setOpenedIndex(index);
    setViewerChart(flat[index].chart);
  }

  function handleRotationChange(chartId: number, degrees: RotationDegrees) {
    setChartState((prev) =>
      prev.map((c) => (c.id === chartId ? { ...c, rotation_degrees: degrees } : c)),
    );
  }

  function handleClose() {
    const i = openedIndex;
    setViewerChart(null);
    setOpenedIndex(null);
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

  function toggleSelect(chartId: number) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(chartId)) next.delete(chartId);
      else next.add(chartId);
      return next;
    });
  }

  function exitSelectMode() {
    setSelectMode(false);
    setSelectedIds(new Set());
  }

  function selectAll() {
    setSelectedIds(new Set(flat.map((f) => f.chart.id)));
  }

  function selectNone() {
    setSelectedIds(new Set());
  }

  function printAll() {
    print(flat.map((f) => f.chart));
  }

  function printSelected() {
    const ordered = flat.map((f) => f.chart).filter((c) => selectedIds.has(c.id));
    print(ordered);
  }

  let cursor = 0;
  const selectedCount = selectedIds.size;

  return (
    <>
      <ChartReferenceBanner airac={airac} />

      <div className="chart-grid-toolbar" role="toolbar" aria-label="Print controls">
        {!selectMode && (
          <>
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => setSelectMode(true)}
            >
              <i className="fa-solid fa-square-check" /> {t("chart.print.selectMode")}
            </button>
            <button type="button" className="btn btn-primary" onClick={printAll}>
              <i className="fa-solid fa-print" /> {t("chart.print.all")}
            </button>
          </>
        )}
        {selectMode && (
          <>
            <button type="button" className="btn btn-secondary" onClick={exitSelectMode}>
              <i className="fa-solid fa-xmark" /> {t("chart.print.selectModeExit")}
            </button>
            <button type="button" className="btn btn-ghost" onClick={selectAll}>
              {t("chart.print.selectAll")}
            </button>
            <button type="button" className="btn btn-ghost" onClick={selectNone}>
              {t("chart.print.selectNone")}
            </button>
            <button
              type="button"
              className="btn btn-primary"
              onClick={printSelected}
              disabled={selectedCount === 0}
            >
              <i className="fa-solid fa-print" />{" "}
              {t("chart.print.selected", { n: selectedCount })}
            </button>
          </>
        )}
      </div>

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
                  onPrint={() => print([chart])}
                  selectMode={selectMode}
                  selected={selectedIds.has(chart.id)}
                  onToggleSelect={() => toggleSelect(chart.id)}
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
          chartId={viewerChart.id}
          aerodromeIcao={aerodromeIcao}
          initialRotation={viewerChart.rotation_degrees ?? 0}
          onRotationChange={(deg) => handleRotationChange(viewerChart.id, deg)}
          onPrint={() => print([viewerChart])}
          onPrintView={(snapshot) => printView(snapshot, viewerChart)}
          onClose={handleClose}
        />
      )}
    </>
  );
}
