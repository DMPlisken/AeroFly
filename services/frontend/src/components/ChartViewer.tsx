import { useEffect, useLayoutEffect, useRef, useState } from "react";
import {
  TransformComponent,
  TransformWrapper,
  type ReactZoomPanPinchContentRef,
} from "react-zoom-pan-pinch";

import { setChartRotation, type RotationDegrees } from "@/api/aerodromes";
import type { ChartViewSnapshot } from "@/utils/printDocuments";

interface Props {
  title: string;
  previewUrl: string;
  /** Optional higher-res URL; defaults to swapping _preview -> _print. */
  printUrl?: string;
  /** Chart identity for persisting rotation. */
  chartId?: number;
  aerodromeIcao?: string;
  initialRotation?: RotationDegrees;
  /** Notify parent of new persisted rotation, so the cached chart stays in sync. */
  onRotationChange?: (degrees: RotationDegrees) => void;
  /** Print the currently-viewed chart via the parent (which owns context + labels). */
  onPrint?: () => void;
  /** Print only the visible viewport (requires the parent to handle the snapshot). */
  onPrintView?: (snapshot: ChartViewSnapshot) => void;
  onClose: () => void;
}

function derivePrintUrl(previewUrl: string): string {
  return previewUrl.replace(/_preview(\.(png|jpg|jpeg))$/i, "_print$1");
}

function nextRotation(current: RotationDegrees, delta: 90 | -90): RotationDegrees {
  const result = (current + delta + 360) % 360;
  return result as RotationDegrees;
}

export function ChartViewer({
  title,
  previewUrl,
  printUrl,
  chartId,
  aerodromeIcao,
  initialRotation = 0,
  onRotationChange,
  onPrint,
  onPrintView,
  onClose,
}: Props) {
  const hiRes = printUrl ?? derivePrintUrl(previewUrl);
  const [src, setSrc] = useState(hiRes);
  const [rotation, setRotation] = useState<RotationDegrees>(initialRotation);
  const [stageSize, setStageSize] = useState<{ w: number; h: number }>({ w: 0, h: 0 });
  const [transform, setTransform] = useState<{ scale: number; positionX: number; positionY: number }>({
    scale: 1,
    positionX: 0,
    positionY: 0,
  });
  const containerRef = useRef<HTMLDivElement | null>(null);
  const imgRef = useRef<HTMLImageElement | null>(null);

  const isQuarterRotated = rotation === 90 || rotation === 270;
  const canPersist = chartId !== undefined && aerodromeIcao !== undefined;
  const isViewModified =
    transform.scale !== 1 || transform.positionX !== 0 || transform.positionY !== 0;

  function handleError() {
    if (src !== previewUrl) setSrc(previewUrl);
  }

  function persistRotation(degrees: RotationDegrees) {
    setRotation(degrees);
    onRotationChange?.(degrees);
    if (!canPersist) return;
    setChartRotation(aerodromeIcao!, chartId!, degrees).catch((err) => {
      console.error("Failed to persist chart rotation", err);
    });
  }

  function rotateLeft() {
    persistRotation(nextRotation(rotation, -90));
  }
  function rotateRight() {
    persistRotation(nextRotation(rotation, 90));
  }
  function resetRotation() {
    persistRotation(0);
  }

  function handlePrintView() {
    if (!onPrintView) return;
    const root = containerRef.current;
    const stage = root?.querySelector(".chart-viewer-stage") as HTMLElement | null;
    const img = imgRef.current;
    if (!stage || !img) return;
    onPrintView({
      imgEl: img,
      stageEl: stage,
      highResUrl: hiRes,
      fallbackUrl: previewUrl,
      scale: transform.scale,
      positionX: transform.positionX,
      positionY: transform.positionY,
      rotation,
    });
  }

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") onClose();
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    return () => {
      document.body.style.overflow = prev;
    };
  }, []);

  // Measure the visible stage (RZPP wrapper) so we can keep the rotated image
  // fit-to-screen at 90°/270°. We re-measure only on rotation change and on
  // window resize — never via ResizeObserver on the stage itself, because the
  // image's bounds we set in turn affect layout and would cause a feedback loop.
  useLayoutEffect(() => {
    const root = containerRef.current;
    if (!root) return;
    const stage = root.querySelector(".chart-viewer-stage") as HTMLElement | null;
    if (!stage) return;
    const rect = stage.getBoundingClientRect();
    setStageSize({ w: rect.width, h: rect.height });
  }, [rotation]);

  useEffect(() => {
    function onResize() {
      const root = containerRef.current;
      if (!root) return;
      const stage = root.querySelector(".chart-viewer-stage") as HTMLElement | null;
      if (!stage) return;
      const rect = stage.getBoundingClientRect();
      setStageSize({ w: rect.width, h: rect.height });
    }
    window.addEventListener("resize", onResize);
    return () => window.removeEventListener("resize", onResize);
  }, []);

  const imgStyle: React.CSSProperties = {
    transform: `rotate(${rotation}deg)`,
    transition: "transform 200ms ease",
  };
  if (isQuarterRotated && stageSize.w && stageSize.h) {
    // After a 90/270 rotation the visual width = CSS height and vice versa.
    // Cap the image's CSS box so the rotated visual fits the un-rotated stage.
    imgStyle.maxWidth = `${stageSize.h}px`;
    imgStyle.maxHeight = `${stageSize.w}px`;
  }

  return (
    <div
      className="chart-viewer-backdrop"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={title}
    >
      <div className="chart-viewer" ref={containerRef} onClick={(e) => e.stopPropagation()}>
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
          onTransformed={(_ref, state) =>
            setTransform({
              scale: state.scale,
              positionX: state.positionX,
              positionY: state.positionY,
            })
          }
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
                  <i className="fa-solid fa-magnifying-glass" />
                </button>
                <span className="chart-viewer-controls-divider" aria-hidden="true" />
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Rotate 90° left"
                  onClick={rotateLeft}
                >
                  <i className="fa-solid fa-rotate-left" />
                </button>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Rotate 90° right"
                  onClick={rotateRight}
                >
                  <i className="fa-solid fa-rotate-right" />
                </button>
                <button
                  type="button"
                  className="icon-button"
                  aria-label="Reset rotation"
                  onClick={resetRotation}
                  disabled={rotation === 0}
                >
                  <i className="fa-solid fa-arrows-up-down-left-right" />
                </button>
                {(onPrint || onPrintView) && (
                  <span className="chart-viewer-controls-divider" aria-hidden="true" />
                )}
                {onPrint && (
                  <button
                    type="button"
                    className="icon-button"
                    aria-label="Print full chart"
                    title="Print full chart"
                    onClick={onPrint}
                  >
                    <i className="fa-solid fa-print" />
                  </button>
                )}
                {onPrintView && (
                  <button
                    type="button"
                    className="icon-button"
                    aria-label="Print visible area"
                    title="Print visible area"
                    onClick={handlePrintView}
                    disabled={!isViewModified}
                  >
                    <i className="fa-solid fa-crop" />
                  </button>
                )}
              </div>
              <TransformComponent
                wrapperClass="chart-viewer-stage"
                contentClass="chart-viewer-content"
              >
                <img
                  ref={imgRef}
                  src={src}
                  alt={title}
                  onError={handleError}
                  draggable={false}
                  className="chart-viewer-image"
                  style={imgStyle}
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
