"""Extract JS source code and understand showPage() + print mechanism."""

import asyncio
from playwright.async_api import async_playwright

PAGES_BASE = "https://aip.dfs.de/BasicVFR/2026APR02/pages/"


async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        # Navigate to a document page
        doc_url = PAGES_BASE + "0AA1E6D372ADBBE24E9FF8BD4A47E0A8.html"
        await page.goto(doc_url, wait_until="networkidle", timeout=30000)

        # Extract showPage function definition from the global scope
        show_page_src = await page.evaluate("""() => {
            if (typeof showPage === 'function') return showPage.toString();
            return 'showPage not found';
        }""")
        print("=== showPage() ===")
        print(show_page_src)

        prev_page_src = await page.evaluate("""() => {
            if (typeof prevPage === 'function') return prevPage.toString();
            return 'prevPage not found';
        }""")
        print("\n=== prevPage() ===")
        print(prev_page_src)

        next_page_src = await page.evaluate("""() => {
            if (typeof nextPage === 'function') return nextPage.toString();
            return 'nextPage not found';
        }""")
        print("\n=== nextPage() ===")
        print(next_page_src)

        # Check for any global config variables
        config = await page.evaluate("""() => {
            const result = {};
            // Check common config patterns
            if (typeof aipConfig !== 'undefined') result.aipConfig = aipConfig;
            if (typeof config !== 'undefined') result.config = config;
            if (typeof baseUrl !== 'undefined') result.baseUrl = baseUrl;
            if (typeof pageUrl !== 'undefined') result.pageUrl = pageUrl;
            if (typeof pdfUrl !== 'undefined') result.pdfUrl = pdfUrl;
            if (typeof imageUrl !== 'undefined') result.imageUrl = imageUrl;
            if (typeof printUrl !== 'undefined') result.printUrl = printUrl;
            if (typeof PAGES !== 'undefined') result.PAGES = PAGES;
            if (typeof pages !== 'undefined') result.pages = typeof pages === 'object' ? JSON.stringify(pages).substring(0, 500) : pages;
            if (typeof pageData !== 'undefined') result.pageData = 'exists';
            if (typeof edition !== 'undefined') result.edition = edition;
            if (typeof chapter !== 'undefined') result.chapter = chapter;
            return result;
        }""")
        print("\n=== Global variables ===")
        for k, v in config.items():
            print(f"  {k} = {v}")

        # Get all script content loaded on the page
        scripts = await page.evaluate("""() => {
            const scripts = document.querySelectorAll('script');
            const results = [];
            scripts.forEach(s => {
                if (s.src) results.push({type: 'external', src: s.src});
                else if (s.textContent.trim()) results.push({type: 'inline', content: s.textContent.trim().substring(0, 2000)});
            });
            return results;
        }""")
        print("\n=== Scripts ===")
        for s in scripts:
            if s['type'] == 'external':
                print(f"  External: {s['src']}")
            else:
                print(f"  Inline ({len(s['content'])} chars):")
                print(f"    {s['content'][:500]}")

        # Try to understand the print popup - intercept what showPage does
        print("\n=== Trying showPage() - intercepting popup/new window ===")

        # Listen for popup
        popup_promise = page.wait_for_event("popup", timeout=10000)
        try:
            await page.evaluate("showPage()")
            popup = await popup_promise
            await popup.wait_for_load_state("networkidle", timeout=15000)
            popup_url = popup.url
            print(f"  Popup URL: {popup_url}")

            # Get popup content
            popup_content = await popup.content()
            with open("scripts/dfs_print_popup.html", "w", encoding="utf-8") as f:
                f.write(popup_content)

            # Look for images in popup
            popup_imgs = await popup.query_selector_all("img")
            print(f"  Popup images: {len(popup_imgs)}")
            for img in popup_imgs:
                src = await img.get_attribute("src") or ""
                alt = await img.get_attribute("alt") or ""
                cls = await img.get_attribute("class") or ""
                src_preview = src[:120] if not src.startswith("data:") else f"data:image/png;base64,... ({len(src)} chars)"
                print(f"    src='{src_preview}' alt='{alt}' class='{cls}'")

            await popup.screenshot(path="scripts/dfs_print_popup.png", full_page=True)
            print("  Popup screenshot saved")

            await popup.close()
        except Exception as e:
            print(f"  No popup: {e}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(main())
