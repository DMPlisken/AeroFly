import { useEffect, useState } from "react";
import {
  TransformComponent,
  TransformWrapper,
  type ReactZoomPanPinchContentRef,
} from "react-zoom-pan-pinch";

interface Props {
  title: string;
  previewUrl: string;
  /** Optional higher-res URL; defaults to swapping _preview -> _print. */
  printUrl?: string;
  onClose: () => void;
}

function derivePrintUrl(previewUrl: string): string {
  return previewUrl.replace(/_preview(\.(png|jpg|jpeg))$/i, "_print$1");
}

export function ChartViewer({ title, previewUrl, printUrl, onClose }: Props) {
  const hiRes = printUrl ?? derivePrintUrl(previewUrl);
  const [src, setSrc] = useState(hiRes);

  // If print version 404s, fall back to the preview.
  function handleError() {
    if (src !== previewUrl) setSrc(previewUrl);
  }

  // Esc key closes.
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  // Lock body scroll while viewer is open.
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  return (
    <div
      className="chart-viewer-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div className="chart-viewer" onClick={(e) => e.stopPropagation()}>
        <header className="chart-viewer-head">
          <span className="chart-viewer-title">{title}</span>
          <button
            type="button"
            className="icon-button"
            aria-label="Close"
            onClick={onClose}
          >
            <i className="fa-solid fa-xmark" />
          </button>
        </header>

        <TransformWrapper
          initialScale={1}
          minScale={0.5}
          maxScale={8}
          wheel={{ step: 0.15 }}
          doubleClick={{ mode: "toggle", step: 2 }}
          pinch={{ step: 5 }}
          limitToBounds={false}
          centerOnInit
        >
          {(utils: ReactZoomPanPinchContentRef) => (
            <>
              <div className="chart-viewer-controls">
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Zoom in"
                  onClick={() => utils.zoomIn(0.3)}
                >
                  <i className="fa-solid fa-plus" />
                </button>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Zoom out"
                  onClick={() => utils.zoomOut(0.3)}
                >
                  <i className="fa-solid fa-minus" />
                </button>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Reset zoom"
                  onClick={() => utils.resetTransform()}
                >
                  <i className="fa-solid fa-rotate-left" />
                </button>
              </div>
              <TransformComponent
                wrapperClass="chart-viewer-stage"
                contentClass="chart-viewer-content"
              >
                <img
                  src={src}
                  alt={title}
                  onError={handleError}
                  draggable={false}
                  className="chart-viewer-image"
                />
              </TransformComponent>
            </>
          )}
        </TransformWrapper>

        <footer className="chart-viewer-foot">
          <span>
            <i className="fa-solid fa-computer-mouse" /> Scroll zum Zoomen · Ziehen zum Verschieben ·{" "}
            <kbd>Esc</kbd> schließt
          </span>
        </footer>
      </div>
    </div>
  );
}
