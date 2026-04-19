import { describe, expect, it } from "vitest";

import type { Chart } from "@/api/aerodromes";

import { groupChartsByType } from "./groupChartsByType";

function chart(partial: Partial<Chart>): Chart {
  return {
    id: partial.id ?? 0,
    chart_type: partial.chart_type ?? "general",
    title: partial.title ?? "",
    title_de: null,
    source_url: "https://example.test/x",
    preview_url: null,
    ...partial,
  } as Chart;
}

describe("groupChartsByType", () => {
  it("returns groups in canonical display order", () => {
    const input = [
      chart({ id: 1, chart_type: "general" }),
      chart({ id: 2, chart_type: "ad_info" }),
      chart({ id: 3, chart_type: "ad_chart" }),
    ];
    const out = groupChartsByType(input);
    expect(out.map((g) => g.type)).toEqual(["ad_info", "ad_chart", "general"]);
  });

  it("preserves input order within a group", () => {
    const input = [
      chart({ id: 1, chart_type: "general", title: "A" }),
      chart({ id: 2, chart_type: "general", title: "B" }),
      chart({ id: 3, chart_type: "general", title: "C" }),
    ];
    const out = groupChartsByType(input);
    expect(out[0].charts.map((c) => c.title)).toEqual(["A", "B", "C"]);
  });

  it("omits empty groups", () => {
    const input = [chart({ id: 1, chart_type: "ad_chart" })];
    const out = groupChartsByType(input);
    expect(out).toHaveLength(1);
    expect(out[0].type).toBe("ad_chart");
  });

  it("buckets unknown chart_type into 'other'", () => {
    const input = [chart({ id: 1, chart_type: "mystery" })];
    const out = groupChartsByType(input);
    expect(out).toHaveLength(1);
    expect(out[0].type).toBe("other");
  });

  it("returns empty array for empty input", () => {
    expect(groupChartsByType([])).toEqual([]);
  });
});
