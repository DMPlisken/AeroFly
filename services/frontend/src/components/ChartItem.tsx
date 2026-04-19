import { useState } from "react";

import type { Chart } from "@/api/aerodromes";

interface Props {
  chart: Chart;
  defaultOpen?: boolean;
}

export function ChartItem({ chart, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const canPreview = Boolean(chart.preview_url);

  return (
    <li className="chart-item">
      <div className="chart-item-head">
        <button
          type="button"
          className="chart-item-toggle"
          onClick={() => canPreview && setOpen((v) => !v)}
          disabled={!canPreview}
          aria-expanded={open}
          aria-controls={`chart-body-${chart.id}`}
        >
          <i
            className={`fa-solid fa-chevron-${open ? "down" : "right"}`}
            style={{ opacity: canPreview ? 1 : 0.3 }}
            aria-hidden="true"
          />
          <i className="fa-solid fa-file-lines chart-item-icon" aria-hidden="true" />
          <span className="chart-item-title">{chart.title}</span>
        </button>
        <a
          href={chart.source_url}
          target="_blank"
          rel="noreferrer"
          className="btn btn-ghost btn-sm"
        >
          <i className="fa-solid fa-arrow-up-right-from-square" /> DFS
        </a>
      </div>
      {open && canPreview && (
        <div id={`chart-body-${chart.id}`} className="chart-item-body">
          <img
            src={chart.preview_url ?? ""}
            alt={chart.title}
            loading="lazy"
            className="chart-item-image"
          />
        </div>
      )}
    </li>
  );
}
