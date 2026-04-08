import os
import asyncio
from playwright.async_api import async_playwright
from spin_bot.titan_stealth import TitanStealthClient

async def run_verification():
    # 1. Setup Directories
    os.makedirs("/home/jules/verification/videos", exist_ok=True)
    os.makedirs("/home/jules/verification/screenshots", exist_ok=True)

    # 2. Use TitanStealthClient to leverage the injected logic
    client = TitanStealthClient()

    # Initialize playwright directly to control context for video
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)

    # We want to use the setup_browser logic but we need record_video_dir
    # So we'll manually create the context similar to setup_browser
    context = await browser.new_context(
        record_video_dir="/home/jules/verification/videos",
        viewport={'width': 390, 'height': 844}
    )

    page = await context.new_page()

    # Apply the same logic as in TitanStealthClient._apply_ui_sensitivity
    # (Since we are using a manual context here for video recording)
    # We can just call the client's method if we assign the page/context
    client.page = page
    client.context = context
    await client._apply_ui_sensitivity()

    try:
        # Load the mock app
        mock_path = f"file://{os.getcwd()}/tests/mock_app.html"
        # We need to land on a page that is NOT about:blank for some scripts to work reliably
        await page.goto(mock_path)
        await asyncio.sleep(2)

        # Journey 1: Verify Theme & Loader Styling
        print("Verifying Theme & Loader...")
        # Dark Theme Encore
        await page.evaluate("document.documentElement.setAttribute('data-theme', 'dark')")
        await asyncio.sleep(1)

        # Check background color of .app-init-loader-wrap
        bg_color = await page.evaluate("window.getComputedStyle(document.querySelector('.app-init-loader-wrap')).backgroundColor")
        print(f"Dark Encore BG: {bg_color}")
        # #100e26 in RGB is rgb(16, 14, 38)

        # Light Theme
        await page.evaluate("document.documentElement.setAttribute('data-theme', 'light')")
        await asyncio.sleep(1)
        bg_color_light = await page.evaluate("window.getComputedStyle(document.querySelector('.app-init-loader-wrap')).backgroundColor")
        print(f"Light BG: {bg_color_light}")
        # #f4f4f4 is rgb(244, 244, 244)

        await page.screenshot(path="/home/jules/verification/screenshots/theme_verification.png")

        # Journey 2: Verify Login Modal Trigger (via Mock Fetch 401)
        print("Verifying 401 Modal...")
        # Inject a mock fetch that returns 401
        await page.evaluate("""
            (async () => {
                const originalFetch = window.fetch;
                window.fetch = async () => ({ status: 401 });
                await window.fetch('/test');
                // Don't restore fetch yet so we can check visibility
            })();
        """)
        await asyncio.sleep(2)

        modal_exists = await page.locator("#omni-auth-modal").is_visible()
        print(f"Modal Visible: {modal_exists}")

        await page.screenshot(path="/home/jules/verification/screenshots/modal_verification.png")

        # Journey 3: Verify Asset Retry Hook
        print("Verifying Asset Retry...")
        # Trigger a failing asset load
        await page.evaluate("triggerFailingAsset()")
        await asyncio.sleep(3) # Wait for retries

        # Check retries count in console or via window variable
        retries = await page.evaluate("window.assetRetries['https://non-existent-asset.com/script.js']")
        print(f"Asset Retries: {retries}")

        # Check if Fatal Error div exists
        fatal_exists = await page.evaluate("document.body.innerText.includes('Fatal Error')")
        print(f"Fatal Error Displayed: {fatal_exists}")

        await page.screenshot(path="/home/jules/verification/screenshots/asset_retry_verification.png")

    finally:
        await context.close()
        await browser.close()
        await pw.stop()

if __name__ == "__main__":
    asyncio.run(run_verification())
