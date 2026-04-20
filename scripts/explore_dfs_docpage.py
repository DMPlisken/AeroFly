"""Explore DFS AIP document page to find print link and content structure."""

import asyncio
from playwright.async_api import async_playwright

PAGES_BASE = "https://aip.dfs.de/BasicVFR/2026APR02/pages/"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # Navigate to first EDKA document
        doc_url = PAGES_BASE + "0AA1E6D372ADBBE24E9FF8BD4A47E0A8.html"
        print(f"=== Document page: EDKA Aachen-Merzbrueck 1 ===")
        print(f"URL: {doc_url}")
        await page.goto(doc_url, wait_until="networkidle", timeout=30000)

        # ALL links
        print("\n--- All links ---")
        all_links = await page.query_selector_all("a")
        for i, link in enumerate(all_links):
            href = await link.get_attribute("href") or ""
            text = (await link.inner_text()).strip()
            title_attr = await link.get_attribute("title") or ""
            cls = await link.get_attribute("class") or ""
            inner_html = (await link.inner_html()).strip()
            print(f"  [{i}] text='{text[:50]}' href='{href[:100]}' title='{title_attr}' class='{cls}' html='{inner_html[:80]}'")

        # ALL buttons
        print("\n--- All buttons ---")
        buttons = await page.query_selector_all("button")
        for i, btn in enumerate(buttons):
            text = (await btn.inner_text()).strip()
            cls = await btn.get_attribute("class") or ""
            onclick = await btn.get_attribute("onclick") or ""
            print(f"  [{i}] text='{text[:50]}' class='{cls}' onclick='{onclick[:80]}'")

        # ALL images
        print("\n--- All images ---")
        imgs = await page.query_selector_all("img")
        for img in imgs:
            src = await img.get_attribute("src") or ""
            alt = await img.get_attribute("alt") or ""
            cls = await img.get_attribute("class") or ""
            width = await img.get_attribute("width") or ""
            print(f"  src='{src[:100]}' alt='{alt}' class='{cls}' width='{width}'")

        # Look for objects/embeds (PDF viewers)
        print("\n--- Objects/Embeds/Iframes ---")
        embeds = await page.query_selector_all("object, embed, iframe")
        for e in embeds:
            tag = await e.evaluate("el => el.tagName")
            src = await e.get_attribute("src") or await e.get_attribute("data") or ""
            typ = await e.get_attribute("type") or ""
            print(f"  {tag} src/data='{src[:100]}' type='{typ}'")

        # Check the toolbar area more carefully - look for SVG icons
        print("\n--- SVG elements ---")
        svgs = await page.query_selector_all("svg")
        for svg in svgs:
            cls = await svg.get_attribute("class") or ""
            parent = await svg.evaluate("el => el.parentElement ? el.parentElement.tagName + '.' + (el.parentElement.className || '') + ' href=' + (el.parentElement.href || '') : 'none'")
            print(f"  SVG class='{cls}' parent='{parent[:100]}'")

        # Get the toolbar HTML specifically
        print("\n--- Top elements / header / toolbar ---")
        headers = await page.query_selector_all("header, .toolbar, .header, .top, .actions, [class*='tool'], [class*='bar'], [class*='action'], [class*='menu']")
        for h in headers:
            tag = await h.evaluate("el => el.tagName")
            cls = await h.get_attribute("class") or ""
            inner = (await h.inner_html()).strip()
            print(f"  {tag} class='{cls}' innerHTML='{inner[:200]}'")

        # Save full HTML for manual inspection
        content = await page.content()
        with open("scripts/dfs_doc_page_edka1.html", "w", encoding="utf-8") as f:
            f.write(content)
        await page.screenshot(path="scripts/dfs_doc_page_edka1.png", full_page=True)
        print("\nHTML and screenshot saved.")

        # Also check the second and third document
        for name, hash_id in [("EDKA-2", "506213757A270F8E08DB22B880829316"), ("AD2-3", "0782587CE9197B32FBEAF41E3A21BC48")]:
            url = PAGES_BASE + hash_id + ".html"
            print(f"\n=== Document: {name} ===")
            await page.goto(url, wait_until="networkidle", timeout=30000)
            await page.screenshot(path=f"scripts/dfs_doc_{name}.png", full_page=True)
            content = await page.content()
            with open(f"scripts/dfs_doc_{name}.html", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"  Saved HTML and screenshot for {name}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
