"""Playwright-driven DFS BasicVFR scraping.

Adapted from `scripts/scrape_dfs_aip.py` to live inside a long-running
FastAPI service. The CLI script still works as before; this module is
the version called from HTTP requests.

Per-airport flow (`scrape_one`):
  1. Look up the airport's chapter hash from a cached `airport_index.json`
     (produced by a prior bulk run — or, in single-airport mode, refreshed
     on demand from the letter pages).
  2. Open a Chromium context, navigate to the chapter page, list documents.
  3. For each document, navigate, capture the inline preview image, open
     the print popup, capture the higher-res print image.
  4. Write everything to `<data_dir>/<ICAO>/` plus a `manifest.json`.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import random
import re
import time
from pathlib import Path

import httpx
from playwright.async_api import BrowserContext, Page, async_playwright

from app.core.config import settings
from app.scraper.classifier import (
    classify_chart_type,
    extract_chart_suffix,
    extract_icao,
    normalize_filename,
)
from app.scraper.models import AirportInfo, DocumentInfo

log = logging.getLogger(__name__)

# Letter group names look like "A", "B", "C-D", … "V-Z".
_LETTER_GROUP_RE = re.compile(r"^[A-Z](?:-[A-Z])?$")


def _chapter_url(edition: str, chapter_hash: str) -> str:
    return f"{settings.dfs_base_url}/BasicVFR/{edition}/chapter/{chapter_hash}.html"


def _page_url(edition: str, page_hash: str) -> str:
    return f"{settings.dfs_base_url}/BasicVFR/{edition}/pages/{page_hash}.html"


def _airport_index_path() -> Path:
    return settings.data_dir / "airport_index.json"


async def _polite_delay() -> None:
    await asyncio.sleep(random.uniform(settings.delay_min, settings.delay_max))


def _save_base64_image(base64_data: str, filepath: Path) -> bool:
    try:
        if "," in base64_data:
            base64_data = base64_data.split(",", 1)[1]
        img_bytes = base64.b64decode(base64_data)
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_bytes(img_bytes)
        log.info("saved %s (%d bytes)", filepath.name, len(img_bytes))
        return True
    except Exception as exc:  # noqa: BLE001
        log.error("failed to save %s: %s", filepath, exc)
        return False


def _load_cached_airport(icao: str, edition: str) -> AirportInfo | None:
    """Read the airport's chapter hash from the cached index file, if any.

    The chapter hash is edition-specific — DFS regenerates it for every
    AIRAC cycle. If the cached index was scraped against a different
    edition than the one we're now serving, we return None so the caller
    re-discovers everything from scratch.
    """
    path = _airport_index_path()
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        log.error("failed to read airport index %s: %s", path, exc)
        return None
    cached_edition = data.get("edition")
    if cached_edition != edition:
        log.info(
            "airport index edition %s != requested %s — treating cache as stale",
            cached_edition, edition,
        )
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


async def _discover_airports_on_letter(
    page: Page, letter: str, chapter_hash: str, edition: str,
) -> list[AirportInfo]:
    url = _chapter_url(edition, chapter_hash)
    log.info("discovering airports for letter group %s", letter)
    await page.goto(url, wait_until="networkidle", timeout=settings.page_timeout_ms)
    await _polite_delay()

    airports: list[AirportInfo] = []
    for link in await page.query_selector_all("a"):
        href = await link.get_attribute("href") or ""
        text = (await link.inner_text()).strip().replace("\t", " ").replace("\n", " ")
        if not href or "dfs.de" in href or "#" in href:
            continue
        icao = extract_icao(text)
        if not icao or ".html" not in href:
            continue
        hash_match = re.search(r"([a-f0-9]{32})\.html", href)
        if not hash_match:
            continue
        name_part = text.split(icao)[0].strip().rstrip()
        name_part = re.sub(r"\s*[►�]+\s*$", "", name_part).strip()
        airports.append(
            AirportInfo(
                name=name_part,
                icao=icao,
                index_text=text,
                chapter_hash=hash_match.group(1),
            )
        )
    log.info("found %d airports under %s", len(airports), letter)
    return airports


def _parse_folder_children(html: str) -> list[tuple[str, str]]:
    """Return [(hash, en_name)] for each <li class="folder-item"> on a chapter page."""
    out: list[tuple[str, str]] = []
    for item in re.split(r'<li class="folder-item">', html)[1:]:
        h = re.search(r'href="([a-f0-9]{32})\.html"', item)
        en = re.search(r'<span[^>]*lang="en"[^>]*class="folder-name">([^<]+)', item)
        if h and en:
            out.append((h.group(1), en.group(1).strip()))
    return out


async def _discover_letter_pages(edition: str) -> dict[str, str]:
    """Look up the per-edition AD section hash, then the letter sub-page hashes.

    DFS regenerates these hashes every AIRAC cycle. Hardcoding them, as the
    legacy `scripts/scrape_dfs_aip.py` did, only works for the edition the
    constants were written against. We re-discover them per scrape — cheap,
    one HTTP call each, no Playwright needed.
    """
    async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
        root = await client.get(f"{settings.dfs_base_url}/BasicVFR/")
        root.raise_for_status()
        ad_hash: str | None = None
        for h, name in _parse_folder_children(root.text):
            if name.upper().startswith("AD ") and "HELICOPTER" not in name.upper():
                ad_hash = h
                break
        if not ad_hash:
            raise RuntimeError(
                f"Could not find 'AD Aerodromes' section in {root.url}"
            )
        ad_resp = await client.get(
            f"{settings.dfs_base_url}/BasicVFR/{edition}/chapter/{ad_hash}.html"
        )
        ad_resp.raise_for_status()

    letters: dict[str, str] = {}
    for h, name in _parse_folder_children(ad_resp.text):
        if _LETTER_GROUP_RE.match(name):
            letters[name] = h
    if not letters:
        raise RuntimeError(
            f"AD section had no letter groups for edition {edition} — "
            "DFS site structure may have changed."
        )
    log.info("discovered %d letter-group hashes for edition %s", len(letters), edition)
    return letters


async def _build_or_refresh_airport_index(
    page: Page, edition: str,
) -> list[AirportInfo]:
    letter_pages = await _discover_letter_pages(edition)
    all_airports: list[AirportInfo] = []
    for letter, chapter_hash in letter_pages.items():
        all_airports.extend(
            await _discover_airports_on_letter(page, letter, chapter_hash, edition)
        )
    settings.data_dir.mkdir(parents=True, exist_ok=True)
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
    _airport_index_path().write_text(
        json.dumps(index_data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("airport index refreshed: %d airports for edition %s", len(all_airports), edition)
    return all_airports


async def _discover_documents(
    page: Page, airport: AirportInfo, edition: str,
) -> list[DocumentInfo]:
    url = _chapter_url(edition, airport.chapter_hash)
    await page.goto(url, wait_until="networkidle", timeout=settings.page_timeout_ms)
    await _polite_delay()

    documents: list[DocumentInfo] = []
    for link in await page.query_selector_all("a"):
        href = await link.get_attribute("href") or ""
        text = (await link.inner_text()).strip().replace("\t", " ").replace("\n", " ")
        if "../pages/" not in href or ".html" not in href:
            continue
        hash_match = re.search(r"([A-F0-9]{32})\.html", href)
        if not hash_match:
            continue
        page_hash = hash_match.group(1)
        clean_text = re.sub(r"\s*[►�]+\s*$", "", text).strip()
        documents.append(
            DocumentInfo(
                dfs_name=clean_text,
                normalized_name=normalize_filename(clean_text),
                page_hash=page_hash,
                page_url=_page_url(edition, page_hash),
                chart_type=classify_chart_type(clean_text),
                chart_suffix=extract_chart_suffix(clean_text),
            )
        )
    log.info("found %d documents for %s", len(documents), airport.icao)
    return documents


async def _open_print_popup(page: Page, context: BrowserContext):
    try:
        async with context.expect_page(timeout=15_000) as popup_info:
            await page.evaluate("showPage()")
        popup = await popup_info.value
        await popup.wait_for_load_state("networkidle", timeout=settings.page_timeout_ms)
        return popup
    except Exception as exc:  # noqa: BLE001
        log.error("could not open print popup: %s", exc)
        return None


async def _download_document(
    page: Page, context: BrowserContext, doc: DocumentInfo, airport_dir: Path,
) -> DocumentInfo:
    log.info("downloading: %s [%s]", doc.dfs_name, doc.chart_type)
    try:
        await page.goto(doc.page_url, wait_until="networkidle", timeout=settings.page_timeout_ms)
        await _polite_delay()

        script_vars = await page.evaluate("""() => ({
            myURL: typeof myURL !== 'undefined' ? myURL : null,
            myPermalink: typeof myPermalink !== 'undefined' ? myPermalink : null,
        })""")
        doc.my_url = script_vars.get("myURL", "") or ""
        doc.permalink = script_vars.get("myPermalink", "") or ""

        preview_src = await page.evaluate(
            """() => { const img = document.querySelector('img.pageImage'); return img ? img.src : null; }"""
        )
        if preview_src and preview_src.startswith("data:image"):
            preview_path = airport_dir / f"{doc.normalized_name}_preview.png"
            if _save_base64_image(preview_src, preview_path):
                doc.preview_file = preview_path.name
        else:
            log.warning("no preview image for %s", doc.dfs_name)

        if doc.my_url:
            try:
                popup = await _open_print_popup(page, context)
                if popup:
                    print_src = await popup.evaluate(
                        """() => { const img = document.querySelector('img'); return img ? img.src : null; }"""
                    )
                    if print_src and print_src.startswith("data:image"):
                        print_path = airport_dir / f"{doc.normalized_name}_print.png"
                        if _save_base64_image(print_src, print_path):
                            doc.print_file = print_path.name
                    else:
                        log.warning("no print image for %s", doc.dfs_name)
                    await popup.close()
                    await _polite_delay()
            except Exception as exc:  # noqa: BLE001
                log.error("print download failed for %s: %s", doc.dfs_name, exc)
                doc.error = f"Print download failed: {exc}"
        else:
            log.warning("no myURL for %s — skipping print version", doc.dfs_name)

    except Exception as exc:  # noqa: BLE001
        log.error("failed to download %s: %s", doc.dfs_name, exc)
        doc.error = str(exc)

    return doc


async def _scrape_one_airport(
    page: Page, context: BrowserContext, airport: AirportInfo, edition: str,
) -> AirportInfo:
    log.info("=" * 60)
    log.info("scraping %s — %s", airport.icao, airport.name)
    airport_dir = settings.data_dir / airport.icao
    airport_dir.mkdir(parents=True, exist_ok=True)

    airport.documents = await _discover_documents(page, airport, edition)
    for i, doc in enumerate(airport.documents, start=1):
        log.info("  [%d/%d] %s", i, len(airport.documents), doc.dfs_name)
        await _download_document(page, context, doc, airport_dir)

    manifest = {
        "icao": airport.icao,
        "name": airport.name,
        "edition": edition,
        "scraped_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "documents": [
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
            for d in airport.documents
        ],
    }
    manifest_path = airport_dir / "manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    log.info("manifest saved: %s", manifest_path)
    return airport


async def scrape_one(icao: str, edition: str) -> dict:
    """Scrape a single aerodrome. Returns a summary dict.

    Requires either a cached `airport_index.json` containing the ICAO,
    or — if the cache is missing/stale — a fresh letter-page crawl which
    takes a few extra minutes.
    """
    icao = icao.strip().upper()
    settings.data_dir.mkdir(parents=True, exist_ok=True)

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

        airport = _load_cached_airport(icao, edition)
        if airport is None:
            log.info("cache miss for %s @ %s — refreshing airport index", icao, edition)
            airports = await _build_or_refresh_airport_index(page, edition)
            airport = next((a for a in airports if a.icao == icao), None)
            if airport is None:
                await browser.close()
                raise ValueError(
                    f"ICAO {icao} not found in any DFS letter page for "
                    f"edition {edition}"
                )

        try:
            result = await _scrape_one_airport(page, context, airport, edition)
            return {
                "icao": result.icao,
                "edition": edition,
                "documents": len(result.documents),
                "errors": [
                    {"dfs_name": d.dfs_name, "error": d.error}
                    for d in result.documents
                    if d.error
                ],
            }
        finally:
            await browser.close()
