import { useState } from "react";

import type { Chart } from "@/api/aerodromes";
import { ChartViewer } from "./ChartViewer";

interface Props {
  chart: Chart;
  defaultOpen?: boolean;
}

export function ChartItem({ chart, defaultOpen = false }: Props) {
  const [open, setOpen] = useState(defaultOpen);
  const [viewerOpen, setViewerOpen] = useState(false);
  const canPreview = Boolean(chart.preview_url);

  return (
    <>
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
          {canPreview && (
            <button
              type="button"
              className="icon-button"
              aria-label="Open large viewer"
              onClick={() => setViewerOpen(true)}
            >
              <i className="fa-solid fa-expand" />
            </button>
          )}
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
            <button
              type="button"
              className="chart-item-image-button"
              onClick={() => setViewerOpen(true)}
              aria-label={`Open ${chart.title} at full size`}
            >
              <img
                src={chart.preview_url ?? ""}
                alt={chart.title}
                loading="lazy"
                className="chart-item-image"
              />
              <span className="chart-item-image-hint">
                <i className="fa-solid fa-magnifying-glass-plus" /> Klick zum Vergrößern
              </span>
            </button>
          </div>
        )}
      </li>
      {viewerOpen && canPreview && chart.preview_url && (
        <ChartViewer
          title={chart.title}
          previewUrl={chart.preview_url}
          onClose={() => setViewerOpen(false)}
        />
      )}
    </>
  );
}
