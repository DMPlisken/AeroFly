"""Explore DFS AIP: letter page -> airport list -> airport documents -> printer link."""

import asyncio
from playwright.async_api import async_playwright

BASE = "https://aip.dfs.de/BasicVFR/2026APR02/chapter/"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Step 1: Navigate to letter "A"
        letter_url = BASE + "a06c61cba08e18621b6435e326113ba5.html"
        print(f"=== Step 1: Letter 'A' page ===")
        print(f"URL: {letter_url}")
        await page.goto(letter_url, wait_until="networkidle", timeout=30000)

        # Get all links
        links = await page.query_selector_all("a")
        print(f"Total links: {len(links)}")
        for i, link in enumerate(links[:50]):
            href = await link.get_attribute("href")
            text = (await link.inner_text()).strip()
            if text and href:
                print(f"  [{i}] '{text[:80]}' -> {href}")

        # Save HTML
        content = await page.content()
        with open("scripts/dfs_letter_a.html", "w", encoding="utf-8") as f:
            f.write(content)

        # Take screenshot
        await page.screenshot(path="scripts/dfs_letter_a.png", full_page=True)

        # Step 2: Click on first airport link (should be an ICAO code link)
        # From the links, find one that looks like an airport page
        airport_links = []
        for link in links:
            href = await link.get_attribute("href")
            text = (await link.inner_text()).strip()
            if href and text and ".html" in str(href) and "ED" in text[:4]:
                airport_links.append((text, href))

        print(f"\n=== Airport links found: {len(airport_links)} ===")
        for text, href in airport_links[:10]:
            print(f"  '{text[:60]}' -> {href}")

        if airport_links:
            first_airport_text, first_airport_href = airport_links[0]
            # Navigate to first airport
            if first_airport_href.startswith("http"):
                airport_url = first_airport_href
            else:
                airport_url = BASE + first_airport_href
            print(f"\n=== Step 2: First airport '{first_airport_text}' ===")
            print(f"URL: {airport_url}")
            await page.goto(airport_url, wait_until="networkidle", timeout=30000)

            # Get all links on the airport page
            doc_links = await page.query_selector_all("a")
            print(f"Total links on airport page: {len(doc_links)}")
            for i, link in enumerate(doc_links[:50]):
                href = await link.get_attribute("href")
                text = (await link.inner_text()).strip()
                if text and href:
                    print(f"  [{i}] '{text[:80]}' -> {href}")

            # Save HTML
            content = await page.content()
            with open("scripts/dfs_airport_first.html", "w", encoding="utf-8") as f:
                f.write(content)

            await page.screenshot(path="scripts/dfs_airport_first.png", full_page=True)

            # Step 3: Click first document link
            doc_page_links = []
            for link in doc_links:
                href = await link.get_attribute("href")
                text = (await link.inner_text()).strip()
                if href and text and ".html" in str(href) and "AD" in text:
                    doc_page_links.append((text, href))

            print(f"\n=== Document links found: {len(doc_page_links)} ===")
            for text, href in doc_page_links[:15]:
                print(f"  '{text[:80]}' -> {href}")

            if doc_page_links:
                first_doc_text, first_doc_href = doc_page_links[0]
                if first_doc_href.startswith("http"):
                    doc_url = first_doc_href
                else:
                    doc_url = BASE + first_doc_href
                print(f"\n=== Step 3: First document '{first_doc_text}' ===")
                print(f"URL: {doc_url}")
                await page.goto(doc_url, wait_until="networkidle", timeout=30000)

                # Look for print icon / link
                all_links = await page.query_selector_all("a")
                print(f"Total links on document page: {len(all_links)}")
                for i, link in enumerate(all_links):
                    href = await link.get_attribute("href")
                    text = (await link.inner_text()).strip()
                    title_attr = await link.get_attribute("title")
                    cls = await link.get_attribute("class")
                    print(f"  [{i}] text='{text[:40]}' href='{href}' title='{title_attr}' class='{cls}'")

                # Look for print-related elements (icons, buttons)
                print("\n--- Looking for print elements ---")
                print_els = await page.query_selector_all("[class*='print'], [id*='print'], [title*='print'], [title*='Print'], [title*='Druck'], [onclick*='print'], button, .icon, [class*='icon']")
                for el in print_els:
                    tag = await el.evaluate("el => el.tagName")
                    text = (await el.inner_text()).strip()
                    cls = await el.get_attribute("class")
                    href_attr = await el.get_attribute("href")
                    title_attr = await el.get_attribute("title")
                    print(f"  {tag} class='{cls}' href='{href_attr}' title='{title_attr}' text='{text[:40]}'")

                # Save HTML and screenshot
                content = await page.content()
                with open("scripts/dfs_document_first.html", "w", encoding="utf-8") as f:
                    f.write(content)
                await page.screenshot(path="scripts/dfs_document_first.png", full_page=True)

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
