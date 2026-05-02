import type { Chart, RotationDegrees } from "@/api/aerodromes";

export interface PrintAerodromeContext {
  icao: string;
  name: string;
  airac: string | null;
}

export interface PrintLabels {
  /** "Gedruckt" / "Printed" */
  printedAt: string;
  /** "Seite" / "Page" */
  page: string;
  /** Function turning a chart_type code into a localized group label. */
  typeLabel: (chartType: string) => string;
  /** Function returning the display title for a chart in the active locale. */
  chartTitle: (chart: Chart) => string;
}

interface MeasuredChart {
  chart: Chart;
  printSrc: string;
  rotation: RotationDegrees;
  /** Visual orientation AFTER rotation. */
  isLandscape: boolean;
}

interface PageSpec {
  isLandscape: boolean;
  imageSrc: string;
  alt: string;
  /**
   * Rotation in degrees applied via CSS to the image element, for full-chart
   * prints where the source is the unrotated chart bitmap. For snapshot prints
   * (where the bitmap is already pre-rotated), pass 0.
   */
  rotationDegrees: 0 | 90 | 180 | 270;
  headerTitle: string;
  headerSubtitle: string;
  headerRight: string;
  footerRight: string;
}

const PRINT_ROOT_ID = "aerofly-print-root";

function derivePrintUrl(previewUrl: string): string {
  return previewUrl.replace(/_preview(\.(png|jpg|jpeg))$/i, "_print$1");
}

function loadImage(src: string): Promise<HTMLImageElement> {
  return new Promise((resolve, reject) => {
    const img = new Image();
    img.crossOrigin = "anonymous";
    img.onload = () => resolve(img);
    img.onerror = () => reject(new Error(`Failed to load ${src}`));
    img.src = src;
  });
}

async function measureChart(chart: Chart): Promise<MeasuredChart | null> {
  if (!chart.preview_url) return null;
  const printSrc = derivePrintUrl(chart.preview_url);
  let img: HTMLImageElement;
  try {
    img = await loadImage(printSrc);
  } catch {
    try {
      img = await loadImage(chart.preview_url);
    } catch {
      return null;
    }
  }
  const rotation = chart.rotation_degrees ?? 0;
  const quarterRotated = rotation === 90 || rotation === 270;
  const visualW = quarterRotated ? img.naturalHeight : img.naturalWidth;
  const visualH = quarterRotated ? img.naturalWidth : img.naturalHeight;
  return {
    chart,
    printSrc: img.src,
    rotation,
    isLandscape: visualW > visualH,
  };
}

function formatToday(): string {
  const d = new Date();
  const dd = String(d.getDate()).padStart(2, "0");
  const mm = String(d.getMonth() + 1).padStart(2, "0");
  const yyyy = d.getFullYear();
  return `${dd}.${mm}.${yyyy}`;
}

function buildPage(spec: PageSpec): HTMLElement {
  const page = document.createElement("section");
  page.className = `print-page print-page--${spec.isLandscape ? "landscape" : "portrait"}`;

  const header = document.createElement("header");
  header.className = "print-page-header";
  const lhs = document.createElement("div");
  const lhsTitle = document.createElement("div");
  lhsTitle.className = "lhs-title";
  lhsTitle.textContent = spec.headerTitle;
  const lhsSub = document.createElement("div");
  lhsSub.className = "lhs-sub";
  lhsSub.textContent = spec.headerSubtitle;
  lhs.appendChild(lhsTitle);
  lhs.appendChild(lhsSub);

  const rhs = document.createElement("div");
  rhs.className = "rhs";
  rhs.innerHTML = spec.headerRight;

  header.appendChild(lhs);
  header.appendChild(rhs);

  const wrap = document.createElement("div");
  wrap.className = "print-page-image-wrap";
  const img = document.createElement("img");
  img.className = "print-page-image";
  img.src = spec.imageSrc;
  img.alt = spec.alt;

  // Page interior (paper minus @page margin) and wrap interior (page minus
  // header / footer / wrap padding) — kept in sync with the @media print CSS.
  // Header (~14mm) + footer (~8mm) + wrap padding (~6mm) ≈ 28mm overhead.
  const PAGE_PORTRAIT = { w: 190, h: 277 };
  const PAGE_LANDSCAPE = { w: 277, h: 190 };
  const HEADER_FOOTER_MM = 28;
  const pageMM = spec.isLandscape ? PAGE_LANDSCAPE : PAGE_PORTRAIT;
  const wrapMM = { w: pageMM.w, h: pageMM.h - HEADER_FOOTER_MM };

  if (spec.rotationDegrees === 90 || spec.rotationDegrees === 270) {
    img.style.width = `${wrapMM.h}mm`;
    img.style.height = `${wrapMM.w}mm`;
    img.style.transform = `translate(-50%, -50%) rotate(${spec.rotationDegrees}deg)`;
  } else if (spec.rotationDegrees === 180) {
    img.style.transform = `translate(-50%, -50%) rotate(180deg)`;
  }
  wrap.appendChild(img);

  const footer = document.createElement("footer");
  footer.className = "print-page-footer";
  footer.innerHTML = `<span>AeroFly · DFS AIP</span><span>${spec.footerRight}</span>`;

  page.appendChild(header);
  page.appendChild(wrap);
  page.appendChild(footer);
  return page;
}

function cleanupPrintRoot(): void {
  document.getElementById(PRINT_ROOT_ID)?.remove();
}

function specForChart(
  measured: MeasuredChart,
  index: number,
  total: number,
  ctx: PrintAerodromeContext,
  labels: PrintLabels,
  printedAtDisplay: string,
): PageSpec {
  return {
    isLandscape: measured.isLandscape,
    imageSrc: measured.printSrc,
    alt: labels.chartTitle(measured.chart),
    rotationDegrees: measured.rotation,
    headerTitle: `${ctx.icao} · ${ctx.name}`,
    headerSubtitle: `${labels.typeLabel(measured.chart.chart_type)} · ${labels.chartTitle(measured.chart)}`,
    headerRight: `${labels.printedAt} ${printedAtDisplay}${
      ctx.airac ? `<br/>AIRAC ${ctx.airac}` : ""
    }`,
    footerRight: `${labels.page} ${index + 1} / ${total}`,
  };
}

async function openPrintDialog(pages: HTMLElement[]): Promise<void> {
  cleanupPrintRoot();
  const root = document.createElement("div");
  root.className = "print-root";
  root.id = PRINT_ROOT_ID;
  pages.forEach((p) => root.appendChild(p));
  document.body.appendChild(root);

  const cleanup = () => {
    cleanupPrintRoot();
    window.removeEventListener("afterprint", cleanup);
  };
  window.addEventListener("afterprint", cleanup);

  // Yield so the browser picks up the new DOM + named @page bindings.
  await new Promise((r) => setTimeout(r, 50));
  window.print();
}

/**
 * Open the browser print dialog with the given documents rendered as A4 pages.
 *
 * - One chart per page.
 * - Stored rotation_degrees is applied; per-page orientation (portrait or
 *   landscape) is chosen from the visual aspect ratio after rotation, via
 *   named `@page` rules in the print stylesheet. Mixed orientations in a
 *   single print job are supported.
 * - Hi-res `_print` URL is used; falls back to `preview_url` if not reachable.
 */
export async function printDocuments(
  charts: Chart[],
  ctx: PrintAerodromeContext,
  labels: PrintLabels,
): Promise<void> {
  if (charts.length === 0) return;

  const measured = (await Promise.all(charts.map(measureChart))).filter(
    (m): m is MeasuredChart => m !== null,
  );
  if (measured.length === 0) return;

  const printedAtDisplay = formatToday();
  const pages = measured.map((m, i) =>
    buildPage(specForChart(m, i, measured.length, ctx, labels, printedAtDisplay)),
  );
  await openPrintDialog(pages);
}

export interface ChartViewSnapshot {
  /** The on-screen image element inside RZPP (used only for its CSS-displayed dimensions). */
  imgEl: HTMLImageElement;
  /** The .chart-viewer-stage element (RZPP wrapper with overflow: hidden). */
  stageEl: HTMLElement;
  /** Hi-res print URL of the chart — used as the bitmap source so the printout stays sharp. */
  highResUrl: string;
  /** Fallback URL if highResUrl can't be loaded (typically the preview_url). */
  fallbackUrl: string | null;
  /** Current RZPP transform state. */
  scale: number;
  positionX: number;
  positionY: number;
  /** Stored chart rotation (0/90/180/270). */
  rotation: RotationDegrees;
}

interface CapturedView {
  dataUrl: string;
  isLandscape: boolean;
}

/**
 * Capture exactly what the user sees in the ChartViewer's stage as a flat
 * bitmap. Mirrors RZPP's CSS transform (translate + scale) plus the image's
 * own CSS rotation, then draws the hi-res bitmap into a canvas of stage size.
 *
 * The output is an axis-aligned PNG matching the visible viewport at
 * device-pixel resolution.
 */
export async function captureChartView(
  s: ChartViewSnapshot,
): Promise<CapturedView | null> {
  let highResImg: HTMLImageElement;
  try {
    highResImg = await loadImage(s.highResUrl);
  } catch {
    if (!s.fallbackUrl) return null;
    try {
      highResImg = await loadImage(s.fallbackUrl);
    } catch {
      return null;
    }
  }

  const stageRect = s.stageEl.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;

  // Pre-rotation, pre-RZPP-scale CSS dimensions of the on-screen img element.
  // RZPP scales via CSS transform (which doesn't change offsetWidth/Height),
  // and the img's own `transform: rotate(...)` likewise leaves offset* alone.
  const displayedW = s.imgEl.offsetWidth;
  const displayedH = s.imgEl.offsetHeight;
  if (displayedW === 0 || displayedH === 0 || stageRect.width === 0 || stageRect.height === 0) {
    return null;
  }

  const canvas = document.createElement("canvas");
  canvas.width = Math.max(1, Math.round(stageRect.width * dpr));
  canvas.height = Math.max(1, Math.round(stageRect.height * dpr));
  const ctx2d = canvas.getContext("2d");
  if (!ctx2d) return null;
  ctx2d.imageSmoothingEnabled = true;
  ctx2d.imageSmoothingQuality = "high";

  // Work in CSS pixels; dpr scaling makes the output bitmap higher-res.
  ctx2d.scale(dpr, dpr);

  // DFS charts are black-on-white; fill background so transparent regions print white.
  ctx2d.fillStyle = "#ffffff";
  ctx2d.fillRect(0, 0, stageRect.width, stageRect.height);

  // Mirror RZPP CSS transform applied to .chart-viewer-content:
  //   transform: translate(positionX, positionY) scale(scale)
  // Origin of .chart-viewer-content is at stage top-left.
  ctx2d.translate(s.positionX, s.positionY);
  ctx2d.scale(s.scale, s.scale);

  // Inside .chart-viewer-content (size = stage size at scale 1), the img is
  // flex-centered. Move to img center.
  ctx2d.translate(stageRect.width / 2, stageRect.height / 2);

  // Apply the img's own CSS rotation around its center.
  if (s.rotation !== 0) {
    ctx2d.rotate((s.rotation * Math.PI) / 180);
  }

  // Draw the high-res bitmap at the displayed CSS size, centered.
  ctx2d.drawImage(highResImg, -displayedW / 2, -displayedH / 2, displayedW, displayedH);

  return {
    dataUrl: canvas.toDataURL("image/png"),
    isLandscape: stageRect.width > stageRect.height,
  };
}

/**
 * Capture the current viewer state and open the print dialog with a single
 * A4 page containing the snapshot.
 */
export async function printChartViewSnapshot(
  snap: ChartViewSnapshot,
  chart: Chart,
  ctx: PrintAerodromeContext,
  labels: PrintLabels,
  detailLabel: string,
): Promise<void> {
  const captured = await captureChartView(snap);
  if (!captured) return;

  const printedAtDisplay = formatToday();
  const spec: PageSpec = {
    isLandscape: captured.isLandscape,
    imageSrc: captured.dataUrl,
    alt: labels.chartTitle(chart),
    // Snapshot bitmap is already pre-rotated — don't re-rotate via CSS.
    rotationDegrees: 0,
    headerTitle: `${ctx.icao} · ${ctx.name}`,
    headerSubtitle: `${labels.typeLabel(chart.chart_type)} · ${labels.chartTitle(chart)} (${detailLabel})`,
    headerRight: `${labels.printedAt} ${printedAtDisplay}${
      ctx.airac ? `<br/>AIRAC ${ctx.airac}` : ""
    }`,
    footerRight: `${labels.page} 1 / 1`,
  };
  await openPrintDialog([buildPage(spec)]);
}
