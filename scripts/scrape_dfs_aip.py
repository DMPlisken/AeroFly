"""
AeroFly DFS AIP Scraper — Playwright-based download of aerodrome data.

Navigates the DFS AIP BasicVFR site and downloads both preview and print
(detailed) PNGs for each document attached to an airport's chapter page.

Two modes:
    # Bulk: discover all airports via A-Z index, then scrape each.
    python scripts/scrape_dfs_aip.py --edition 2026APR02
    python scripts/scrape_dfs_aip.py --edition 2026APR02 --limit 5

    # Per-aerodrome (on-demand): scrape one ICAO only. Requires a cached
    # airport_index.json on disk (produced by a prior bulk run).
    python scripts/scrape_dfs_aip.py --edition 2026APR02 --icao EDDM

Documents are stored in:
    data/aerodromes/<ICAO>/
        <normalized_name>_preview.png
        <normalized_name>_print.png
        manifest.json   (maps normalized names to DFS original names + classifies each by chart_type)

Chart type classification is name-based and conservative:
    - "supplement" — shared AD supplements ("AD 2-71", "AD 2-3" etc.)
    - "terminal"   — terminal charts (contain "Terminal Chart" in the DFS name)
    - "aerodrome"  — per-airport numbered/lettered charts (VAC, ADC, ground charts)
    - "other"      — anything that doesn't match the rules above
"""

import argparse
import asyncio
import base64
import json
import logging
import random
import re
import time
from dataclasses import dataclass, field, asdict
from pathlib import Path

from playwright.async_api import async_playwright, Page, BrowserContext

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CHAPTER_BASE = "https://aip.dfs.de/BasicVFR/{edition}/chapter/"
PAGES_BASE = "https://aip.dfs.de/BasicVFR/{edition}/pages/"
PRINT_BASE = "https://aip.dfs.de/basicVFR/print/"

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "aerodromes"
AIRPORT_INDEX_PATH = DATA_DIR / "airport_index.json"

DELAY_MIN = 2.0
DELAY_MAX = 4.0

# Letter index page hashes (from the DFS AIP index page)
# These map letter groups to the hash IDs of their index pages
LETTER_INDEX = {
    "A":   "a06c61cba08e18621b6435e326113ba5",
    "B":   "5f84acaa838719e01944ab0af81d8f58",
    "C-D": "b883df0718062a5173471e5b5fc57b26",
    "E-F": "74e4d29f4ecec3c7d262949d6c158c68",
    "G-H": "5aad4132c041d21d9bc351393b1f2032",
    "I-J": "47b26ba6dda0c4421e6d99c44f85a823",
    "K-L": "8d0c66c1db9a12fd6ff5e0680a373344",
    "M":   "eaf71f57bea2a025652b09b1a8a5654d",
    "N":   "6441b3eaef86d45d85407da19a861a6c",
    "O-P": "2340f35a3c68dce010bdec752cbfd940",
    "Q-R": "3ed566c654fa602fa5fbdb7fbe6e7772",
    "S":   "82ec4b906a61b5835f26609303443b04",
    "T-U": "c1f9fff6a48aa9bb315e62f5c18fb08b",
    "V-Z": "c51bcca901878d65764e10d65a768bf3",
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("dfs-scraper")


# ---------------------------------------------------------------------------
# Chart type classification (pure function, unit-tested)
# ---------------------------------------------------------------------------

_ICAO_RE = re.compile(r"\bED[A-Z]{2}\b")
_AD_SUPPLEMENT_RE = re.compile(r"^\s*AD\s+\d", re.IGNORECASE)
_TRAILING_SUFFIX_RE = re.compile(r"([A-Z0-9]+)\s*$")


def classify_chart_type(dfs_name: str) -> str:
    """Classify a DFS document name into a coarse chart type.

    Rules (checked in order):
      1. supplement: name starts with "AD <digit>" AND contains no airport ICAO.
         Shared references like "AD 2-71", "AD 2-3".
      2. terminal: name contains "Terminal Chart" (case-insensitive).
      3. aerodrome: name starts with an airport ICAO ("EDXX") — covers every
         per-airport chart (VAC, ADC, ground, etc.). Finer subtyping is the
         chart-selector's job and requires image content, not just the name.
      4. other: fallback.
    """
    name = dfs_name.strip()
    upper = name.upper()

    if _AD_SUPPLEMENT_RE.match(upper) and not _ICAO_RE.search(upper):
        return "supplement"
    if "TERMINAL CHART" in upper:
        return "terminal"
    if re.match(r"^ED[A-Z]{2}\b", upper):
        return "aerodrome"
    return "other"


def extract_chart_suffix(dfs_name: str) -> str | None:
    """Return the trailing identifier after the airport portion.

    Examples:
      "EDDM Muenchen 4"           -> "4"
      "EDDH Hamburg 2A"           -> "2A"
      "EDDF Frankfurt Main 1"     -> "1"
      "EDDM Muenchen Terminal Chart 1" -> "1"
      "AD 2-71"                   -> None  (supplement, no airport prefix)
    """
    upper = dfs_name.strip().upper()
    if not re.match(r"^ED[A-Z]{2}\b", upper):
        return None
    match = _TRAILING_SUFFIX_RE.search(upper)
    if match:
        token = match.group(1)
        # Skip if the token is itself the ICAO (short name with nothing after).
        if _ICAO_RE.fullmatch(token):
            return None
        return token
    return None


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class DocumentInfo:
    """A single document within an airport."""
    dfs_name: str
    normalized_name: str
    page_hash: str
    page_url: str
    permalink: str
    my_url: str
    chart_type: str = "other"
    chart_suffix: str | None = None
    preview_file: str | None = None
    print_file: str | None = None
    error: str | None = None


@dataclass
class AirportInfo:
    """An airport entry from the letter index."""
    name: str
    icao: str
    index_text: str
    chapter_hash: str
    documents: list[DocumentInfo] = field(default_factory=list)


@dataclass
class ScrapeManifest:
    """Manifest for an airport's scraped data."""
    icao: str
    name: str
    edition: str
    scraped_at: str
    documents: list[dict] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def random_delay():
    """Sleep for a random duration between DELAY_MIN and DELAY_MAX."""
    delay = random.uniform(DELAY_MIN, DELAY_MAX)
    time.sleep(delay)


def normalize_name(dfs_name: str) -> str:
    """Normalize a DFS document name for use as a filename.

    'EDKA Aachen-Merzbrueck 1' -> 'EDKA_Aachen-Merzbrueck_1'
    'AD 2-3' -> 'AD_2-3'
    """
    normalized = re.sub(r'\s+', '_', dfs_name.strip())
    normalized = re.sub(r'[^\w\-.]', '_', normalized)
    return normalized


def extract_icao(text: str) -> str | None:
    """Extract a 4-letter ICAO code (ED**) from text."""
    match = re.search(r'\b(ED[A-Z]{2})\b', text)
    return match.group(1) if match else None


def save_base64_image(base64_data: str, filepath: Path) -> bool:
    """Decode a base64 image string and save to file."""
    try:
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]
        img_bytes = base64.b64decode(base64_data)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_bytes(img_bytes)
        log.info(f"  Saved: {filepath.name} ({len(img_bytes):,} bytes)")
        return True
    except Exception as e:
        log.error(f"  Failed to save {filepath}: {e}")
        return False


def load_airport_from_index(icao: str) -> AirportInfo | None:
    """Look up an airport's chapter hash from the cached index file.

    Used by --icao mode so we don't have to re-crawl the A-Z letter pages
    on every single-airport run.
    """
    if not AIRPORT_INDEX_PATH.exists():
        return None
    try:
        data = json.loads(AIRPORT_INDEX_PATH.read_text(encoding="utf-8"))
    except Exception as e:
        log.error(f"Failed to read airport index {AIRPORT_INDEX_PATH}: {e}")
        return None
    for entry in data.get("airports", []):
        if entry.get("icao") == icao:
            return AirportInfo(
                name=entry.get("name", ""),
                icao=entry["icao"],
                index_text=entry.get("index_text", ""),
                chapter_hash=entry["chapter_hash"],
            )
    return None


# ---------------------------------------------------------------------------
# Scraper
# ---------------------------------------------------------------------------

async def discover_airports_on_letter_page(
    page: Page, letter: str, chapter_hash: str, edition: str
) -> list[AirportInfo]:
    """Navigate to a letter page and extract all airport entries."""
    url = CHAPTER_BASE.format(edition=edition) + chapter_hash + ".html"
    log.info(f"Discovering airports for letter group '{letter}'...")
    await page.goto(url, wait_until="networkidle", timeout=30000)
    random_delay()

    airports = []
    links = await page.query_selector_all("a")
    for link in links:
        href = await link.get_attribute("href") or ""
        text = (await link.inner_text()).strip().replace("\t", " ").replace("\n", " ")
        if not href or "dfs.de" in href or "#" in href:
            continue
        icao = extract_icao(text)
        if icao and ".html" in href:
            hash_match = re.search(r'([a-f0-9]{32})\.html', href)
            if hash_match:
                chapter_hash_val = hash_match.group(1)
                name_part = text.split(icao)[0].strip().rstrip()
                name_part = re.sub(r'\s*[►�]+\s*$', '', name_part).strip()
                airports.append(AirportInfo(
                    name=name_part,
                    icao=icao,
                    index_text=text,
                    chapter_hash=chapter_hash_val,
                ))

    log.info(f"  Found {len(airports)} airports under '{letter}'")
    return airports


async def discover_documents_for_airport(
    page: Page, airport: AirportInfo, edition: str
) -> list[DocumentInfo]:
    """Navigate to an airport's chapter page and extract document links."""
    url = CHAPTER_BASE.format(edition=edition) + airport.chapter_hash + ".html"
    log.info(f"Discovering documents for {airport.icao} ({airport.name})...")
    await page.goto(url, wait_until="networkidle", timeout=30000)
    random_delay()

    documents = []
    links = await page.query_selector_all("a")
    for link in links:
        href = await link.get_attribute("href") or ""
        text = (await link.inner_text()).strip().replace("\t", " ").replace("\n", " ")
        if "../pages/" in href and ".html" in href:
            hash_match = re.search(r'([A-F0-9]{32})\.html', href)
            if hash_match:
                page_hash = hash_match.group(1)
                clean_text = re.sub(r'\s*[►�]+\s*$', '', text).strip()
                documents.append(DocumentInfo(
                    dfs_name=clean_text,
                    normalized_name=normalize_name(clean_text),
                    page_hash=page_hash,
                    page_url=PAGES_BASE.format(edition=edition) + page_hash + ".html",
                    permalink="",
                    my_url="",
                    chart_type=classify_chart_type(clean_text),
                    chart_suffix=extract_chart_suffix(clean_text),
                ))

    log.info(f"  Found {len(documents)} documents for {airport.icao}")
    return documents


async def download_document(
    page: Page, context: BrowserContext, doc: DocumentInfo, airport_dir: Path
) -> DocumentInfo:
    """Download both preview and print versions of a document."""
    log.info(f"  Downloading: {doc.dfs_name} [{doc.chart_type}]")

    try:
        await page.goto(doc.page_url, wait_until="networkidle", timeout=30000)
        random_delay()

        script_vars = await page.evaluate("""() => {
            return {
                myURL: typeof myURL !== 'undefined' ? myURL : null,
                myPermalink: typeof myPermalink !== 'undefined' ? myPermalink : null,
            };
        }""")
        doc.my_url = script_vars.get("myURL", "") or ""
        doc.permalink = script_vars.get("myPermalink", "") or ""

        preview_src = await page.evaluate("""() => {
            const img = document.querySelector('img.pageImage');
            return img ? img.src : null;
        }""")

        if preview_src and preview_src.startswith("data:image"):
            preview_path = airport_dir / f"{doc.normalized_name}_preview.png"
            if save_base64_image(preview_src, preview_path):
                doc.preview_file = preview_path.name
        else:
            log.warning(f"    No preview image found for {doc.dfs_name}")

        if doc.my_url:
            try:
                popup = await _open_print_popup(page, context)
                if popup:
                    print_src = await popup.evaluate("""() => {
                        const img = document.querySelector('img');
                        return img ? img.src : null;
                    }""")

                    if print_src and print_src.startswith("data:image"):
                        print_path = airport_dir / f"{doc.normalized_name}_print.png"
                        if save_base64_image(print_src, print_path):
                            doc.print_file = print_path.name
                    else:
                        log.warning(f"    No print image found for {doc.dfs_name}")

                    await popup.close()
                    random_delay()
            except Exception as e:
                log.error(f"    Print download failed for {doc.dfs_name}: {e}")
                doc.error = f"Print download failed: {e}"
        else:
            log.warning(f"    No myURL found for {doc.dfs_name}, skipping print version")

    except Exception as e:
        log.error(f"    Failed to download {doc.dfs_name}: {e}")
        doc.error = str(e)

    return doc


async def _open_print_popup(page: Page, context: BrowserContext):
    """Click the print button and capture the popup window."""
    try:
        async with context.expect_page(timeout=15000) as popup_info:
            await page.evaluate("showPage()")
        popup = await popup_info.value
        await popup.wait_for_load_state("networkidle", timeout=30000)
        return popup
    except Exception as e:
        log.error(f"    Could not open print popup: {e}")
        return None


async def scrape_airport(
    page: Page, context: BrowserContext, airport: AirportInfo,
    edition: str
) -> AirportInfo:
    """Scrape all documents for a single airport."""
    log.info(f"{'='*60}")
    log.info(f"Scraping {airport.icao} — {airport.name}")
    log.info(f"{'='*60}")

    airport_dir = DATA_DIR / airport.icao
    airport_dir.mkdir(parents=True, exist_ok=True)

    documents = await discover_documents_for_airport(page, airport, edition)
    airport.documents = documents

    for i, doc in enumerate(documents):
        log.info(f"  [{i+1}/{len(documents)}] {doc.dfs_name}")
        await download_document(page, context, doc, airport_dir)

    manifest = ScrapeManifest(
        icao=airport.icao,
        name=airport.name,
        edition=edition,
        scraped_at=time.strftime("%Y-%m-%dT%H:%M:%S"),
        documents=[
            {
                "dfs_name": d.dfs_name,
                "normalized_name": d.normalized_name,
                "permalink": d.permalink,
                "chart_type": d.chart_type,
                "chart_suffix": d.chart_suffix,
                "preview_file": d.preview_file,
                "print_file": d.print_file,
                "error": d.error,
            }
            for d in documents
        ],
    )
    manifest_path = airport_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(asdict(manifest), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info(f"Manifest saved: {manifest_path}")

    return airport


async def run(
    edition: str,
    *,
    limit: int | None = None,
    icao: str | None = None,
):
    """Main scraper entry point."""
    log.info(f"AeroFly DFS AIP Scraper — Edition: {edition}")
    log.info(f"Output directory: {DATA_DIR}")
    if icao:
        log.info(f"Single-airport mode: {icao}")
    elif limit:
        log.info(f"Limit: {limit} airports")

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={"width": 1920, "height": 1080},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/131.0.0.0 Safari/537.36"
            ),
        )
        page = await context.new_page()

        if icao:
            airport = load_airport_from_index(icao)
            if airport is None:
                log.error(
                    f"ICAO {icao} not found in cached airport index "
                    f"({AIRPORT_INDEX_PATH}). Run a bulk scrape first to populate it."
                )
                await browser.close()
                return
            all_airports = [airport]
        else:
            all_airports = []
            for letter, chapter_hash in LETTER_INDEX.items():
                airports = await discover_airports_on_letter_page(
                    page, letter, chapter_hash, edition
                )
                all_airports.extend(airports)

            log.info(f"\nTotal airports discovered: {len(all_airports)}")

            if limit and limit < len(all_airports):
                all_airports = all_airports[:limit]
                log.info(f"Limited to first {limit} airports")

            index_data = {
                "edition": edition,
                "total_airports": len(all_airports),
                "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "airports": [
                    {
                        "icao": a.icao,
                        "name": a.name,
                        "index_text": a.index_text,
                        "chapter_hash": a.chapter_hash,
                    }
                    for a in all_airports
                ],
            }
            AIRPORT_INDEX_PATH.write_text(
                json.dumps(index_data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            log.info(f"Airport index saved: {AIRPORT_INDEX_PATH}")

        results = {"success": 0, "partial": 0, "failed": 0}
        for i, airport in enumerate(all_airports):
            log.info(f"\n[{i+1}/{len(all_airports)}] Starting {airport.icao}...")
            try:
                await scrape_airport(page, context, airport, edition)
                errors = [d for d in airport.documents if d.error]
                if errors:
                    results["partial"] += 1
                    log.warning(f"  {airport.icao}: {len(errors)} documents had errors")
                else:
                    results["success"] += 1
            except Exception as e:
                results["failed"] += 1
                log.error(f"  {airport.icao} FAILED: {e}")

        log.info(f"\n{'='*60}")
        log.info("SCRAPE COMPLETE")
        log.info(f"{'='*60}")
        log.info(f"  Edition:    {edition}")
        log.info(f"  Airports:   {len(all_airports)}")
        log.info(f"  Successful: {results['success']}")
        log.info(f"  Partial:    {results['partial']}")
        log.info(f"  Failed:     {results['failed']}")
        log.info(f"  Output:     {DATA_DIR}")

        await browser.close()


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scrape DFS AIP BasicVFR aerodrome data"
    )
    parser.add_argument(
        "--edition", default="2026APR02",
        help="DFS AIP edition identifier (default: 2026APR02)",
    )
    parser.add_argument(
        "--limit", type=int, default=None,
        help="Limit to first N airports (bulk mode only; ignored when --icao is set)",
    )
    parser.add_argument(
        "--icao", type=str, default=None,
        help=(
            "Single-airport mode: scrape only the given ICAO (e.g. EDDM). "
            "Requires a cached data/aerodromes/airport_index.json from a prior bulk run."
        ),
    )
    args = parser.parse_args()

    if args.icao:
        args.icao = args.icao.strip().upper()

    asyncio.run(run(edition=args.edition, limit=args.limit, icao=args.icao))


if __name__ == "__main__":
    main()
