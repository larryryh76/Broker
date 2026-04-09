import os
import asyncio
from playwright.async_api import async_playwright
from spin_bot.interaction import TitanInteractionSuite

async def run_verification():
    # 1. Setup Directories
    os.makedirs("verification/videos", exist_ok=True)
    os.makedirs("verification/screenshots", exist_ok=True)

    # Initialize playwright directly to control context for video
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(headless=True)

    context = await browser.new_context(
        record_video_dir="verification/videos",
        viewport={'width': 390, 'height': 844}
    )

    page = await context.new_page()
    page.on("console", lambda msg: print(f"CONSOLE: {msg.text}"))
    page.on("pageerror", lambda exc: print(f"PAGE ERROR: {exc}"))

    # Apply UI sensitivity
    await TitanInteractionSuite.apply_ui_sensitivity(page)

    try:
        # Load the mock app
        mock_path = f"file://{os.getcwd()}/tests/mock_app.html"
        print(f"Navigating to {mock_path}")
        await page.goto(mock_path)
        await asyncio.sleep(2)

        # Journey 1: Verify Theme & Loader Styling
        print("Verifying Theme & Loader...")

        # Dark Theme Encore
        print("Setting theme to dark...")
        await page.evaluate("document.documentElement.setAttribute('data-theme', 'dark')")
        await asyncio.sleep(1)
        bg_color = await page.evaluate("window.getComputedStyle(document.querySelector('.app-init-loader-wrap')).backgroundColor")
        print(f"Dark Encore BG (Expected #100e26 / rgb(16, 14, 38)): {bg_color}")

        # Light Theme
        print("Setting theme to light...")
        await page.evaluate("document.documentElement.setAttribute('data-theme', 'light')")
        await asyncio.sleep(1)
        bg_color_light = await page.evaluate("window.getComputedStyle(document.querySelector('.app-init-loader-wrap')).backgroundColor")
        print(f"Light BG (Expected #f4f4f4 / rgb(244, 244, 244)): {bg_color_light}")

        await page.screenshot(path="verification/screenshots/theme_verification.png")

        # Journey 2: Verify Login Modal Trigger (via Mock Fetch 401)
        print("Verifying 401 Modal...")
        # Use a special trigger for the test
        await page.evaluate("window.fetch('MOCK_401').catch(e => {})")
        await asyncio.sleep(2)

        modal_count = await page.locator("#titan-v5-auth-modal").count()
        print(f"Modal Count: {modal_count}")

        if modal_count > 0:
            z_backdrop = await page.evaluate("window.getComputedStyle(document.querySelector('.titan-modal-backdrop')).zIndex")
            z_content = await page.evaluate("window.getComputedStyle(document.querySelector('.titan-modal-content')).zIndex")
            print(f"Z-Index - Backdrop: {z_backdrop}, Content: {z_content}")

            # Verify primary/secondary buttons exist
            primary = await page.locator("#titan-login-primary").count()
            secondary = await page.locator("#titan-exit-secondary").count()
            print(f"Buttons - Primary: {primary}, Secondary: {secondary}")

        await page.screenshot(path="verification/screenshots/modal_verification.png")

        # Journey 3: Verify Asset Retry Hook
        print("Verifying Asset Retry...")
        # Trigger a failing asset load
        await page.evaluate("triggerFailingAsset()")
        await asyncio.sleep(5) # Wait for retries

        # Check retries count in console or via window variable
        retries = await page.evaluate("window.assetRetries['https://non-existent-asset.com/script.js']")
        print(f"Asset Retries: {retries}")

        await page.screenshot(path="verification/screenshots/asset_retry_verification.png")

    finally:
        await context.close()
        await browser.close()
        await pw.stop()

if __name__ == "__main__":
    asyncio.run(run_verification())
