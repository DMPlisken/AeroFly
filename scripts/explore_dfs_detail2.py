"""Explore DFS AIP: airport page -> documents -> print link."""

import asyncio
import re
from playwright.async_api import async_playwright

BASE = "https://aip.dfs.de/BasicVFR/2026APR02/chapter/"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Step 1: Go to first airport (Aachen-Merzbrueck EDKA)
        airport_url = BASE + "8143d916d387f89cf9caa358fae3da64.html"
        print(f"=== Step 1: Airport page (EDKA) ===")
        await page.goto(airport_url, wait_until="networkidle", timeout=30000)

        links = await page.query_selector_all("a")
        print(f"Total links: {len(links)}")
        for i, link in enumerate(links):
            href = await link.get_attribute("href")
            text = (await link.inner_text()).strip().replace("\n", " ").replace("\t", " ")
            if text and href:
                print(f"  [{i}] '{text[:80]}' -> {href}")

        content = await page.content()
        with open("scripts/dfs_airport_edka.html", "w", encoding="utf-8") as f:
            f.write(content)
        await page.screenshot(path="scripts/dfs_airport_edka.png", full_page=True)

        # Step 2: Find document links (AD 2 EDKA ...)
        doc_links = []
        for link in links:
            href = await link.get_attribute("href")
            text = (await link.inner_text()).strip().replace("\n", " ").replace("\t", " ")
            if href and text and ".html" in str(href):
                if re.search(r'AD\s+2\s+ED', text):
                    doc_links.append((text, href))

        print(f"\n=== Document links: {len(doc_links)} ===")
        for text, href in doc_links:
            print(f"  '{text[:80]}' -> {href}")

        # Step 3: Navigate to first document
        if doc_links:
            first_text, first_href = doc_links[0]
            doc_url = BASE + first_href if not first_href.startswith("http") else first_href
            print(f"\n=== Step 2: First document '{first_text}' ===")
            print(f"URL: {doc_url}")
            await page.goto(doc_url, wait_until="networkidle", timeout=30000)

            # Get ALL elements in the page, especially the toolbar area
            print("\n--- All links on document page ---")
            all_links = await page.query_selector_all("a")
            for i, link in enumerate(all_links):
                href = await link.get_attribute("href") or ""
                text = (await link.inner_text()).strip()
                title_attr = await link.get_attribute("title") or ""
                cls = await link.get_attribute("class") or ""
                onclick = await link.get_attribute("onclick") or ""
                inner_html = await link.inner_html()
                print(f"  [{i}] text='{text[:40]}' href='{href[:80]}' title='{title_attr}' class='{cls}' onclick='{onclick[:40]}' innerHTML='{inner_html[:60]}'")

            # Look for any icon/image that could be a print button
            print("\n--- Images/icons ---")
            imgs = await page.query_selector_all("img, svg, i, span.icon, [class*='fa-'], [class*='icon'], [class*='glyphicon']")
            for img in imgs:
                tag = await img.evaluate("el => el.tagName")
                cls = await img.get_attribute("class") or ""
                src = await img.get_attribute("src") or ""
                alt = await img.get_attribute("alt") or ""
                title = await img.get_attribute("title") or ""
                print(f"  {tag} class='{cls}' src='{src[:60]}' alt='{alt}' title='{title}'")

            # Check for iframes (documents might be in an iframe)
            print("\n--- Iframes ---")
            iframes = await page.query_selector_all("iframe, object, embed")
            for iframe in iframes:
                tag = await iframe.evaluate("el => el.tagName")
                src = await iframe.get_attribute("src") or ""
                cls = await iframe.get_attribute("class") or ""
                print(f"  {tag} src='{src[:100]}' class='{cls}'")

            content = await page.content()
            with open("scripts/dfs_document_edka.html", "w", encoding="utf-8") as f:
                f.write(content)
            await page.screenshot(path="scripts/dfs_document_edka.png", full_page=True)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
