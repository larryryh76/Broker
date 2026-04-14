import asyncio
import os
from playwright.async_api import async_playwright

async def run_diagnostic():
    # Ensure artifacts directory exists
    os.makedirs("artifacts", exist_ok=True)

    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=True)
        # Use a mobile-like context
        context = await browser.new_context(
            viewport={'width': 375, 'height': 812},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/04.1"
        )
        page = await context.new_page()

        print("Navigating to https://www.football.com/ng/m/ ...")
        await page.goto("https://www.football.com/ng/m/", wait_until="networkidle")

        print("Waiting 10 seconds for scripts/loaders...")
        await asyncio.sleep(10)

        # Screenshot
        print("Capturing screenshot...")
        await page.screenshot(path="artifacts/diagnostic_view.png", full_page=True)

        # HTML Dump
        print("Capturing HTML dump...")
        content = await page.content()
        with open("artifacts/source_dump.html", "w", encoding="utf-8") as f:
            f.write(content)

        print("Diagnostic complete. Files saved in artifacts/")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_diagnostic())
