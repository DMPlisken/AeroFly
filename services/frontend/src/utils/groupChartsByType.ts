import type { Chart } from "@/api/aerodromes";

/**
 * Canonical display order for chart-type groups.
 * - Matches the order a pilot mentally walks through during briefing:
 *   basic info → visuals → approach → taxi → generic fallbacks
 * - Only groups that actually have charts are returned.
 * - Within each group, input order is preserved (= manifest / scraper order
 *   = DFS authority). No sorting, ever.
 */
const GROUP_ORDER = [
  "ad_info",
  "ad_chart",
  "parking",
  "taxi",
  "sid",
  "star",
  "iac",
  "vac",
  "general",
  "other",
] as const;

export type ChartGroupKey = (typeof GROUP_ORDER)[number];

export interface ChartGroup {
  type: ChartGroupKey;
  charts: Chart[];
}

const KNOWN = new Set<string>(GROUP_ORDER);

export function groupChartsByType(charts: Chart[]): ChartGroup[] {
  const buckets = new Map<ChartGroupKey, Chart[]>();
  for (const chart of charts) {
    const key: ChartGroupKey = KNOWN.has(chart.chart_type)
      ? (chart.chart_type as ChartGroupKey)
      : "other";
    const list = buckets.get(key);
    if (list) list.push(chart);
    else buckets.set(key, [chart]);
  }
  const result: ChartGroup[] = [];
  for (const type of GROUP_ORDER) {
    const group = buckets.get(type);
    if (group && group.length > 0) {
      result.push({ type, charts: group });
    }
  }
  return result;
}
