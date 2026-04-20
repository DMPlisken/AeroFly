"""Quick exploration of DFS AIP page structure."""

import asyncio
from playwright.async_api import async_playwright


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        url = "https://aip.dfs.de/BasicVFR/2026APR02/chapter/2e3e6324f051cd9f8406e692e8843084.html"
        print(f"Navigating to: {url}")
        await page.goto(url, wait_until="networkidle", timeout=30000)

        # Get page title
        title = await page.title()
        print(f"Page title: {title}")

        # Get the full HTML structure to understand the index
        content = await page.content()

        # Look for letter index links
        letter_links = await page.query_selector_all("a")
        print(f"\nTotal links on page: {len(letter_links)}")

        # Print first 50 links to understand structure
        for i, link in enumerate(letter_links[:80]):
            href = await link.get_attribute("href")
            text = (await link.inner_text()).strip()
            if text:
                print(f"  [{i}] text='{text[:60]}' href='{href}'")

        # Look for any navigation/index structure
        print("\n--- Looking for nav/index structure ---")
        navs = await page.query_selector_all("nav, .index, .nav, #index, .sidebar, .toc, ul.toc")
        print(f"Nav elements found: {len(navs)}")

        # Look for headings
        headings = await page.query_selector_all("h1, h2, h3, h4")
        for h in headings[:20]:
            tag = await h.evaluate("el => el.tagName")
            text = (await h.inner_text()).strip()
            print(f"  {tag}: {text[:80]}")

        # Save full page HTML for analysis
        with open("scripts/dfs_index_page.html", "w", encoding="utf-8") as f:
            f.write(content)
        print("\nFull HTML saved to scripts/dfs_index_page.html")

        # Take a screenshot
        await page.screenshot(path="scripts/dfs_index_screenshot.png", full_page=True)
        print("Screenshot saved to scripts/dfs_index_screenshot.png")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
