import os
import asyncio
import random
from playwright.async_api import async_playwright, Page, BrowserContext
from spin_bot.database import TitanDatabase
from spin_bot.interaction import TitanInteractionSuite
from typing import List, Dict, Optional, Any

class TitanGameEngine:
    def __init__(self, db: TitanDatabase):
        self.db = db
        # V5.45: Deep-link is unstable in SPA; target the Lobby instead
        self.game_url = "https://www.football.com/ng/m/games"

    async def get_frame(self, page: Page):
        """V5.45: Lobby-Thumbnail Navigation & Iframe Sync."""
        print("DEBUG: Executing Render-Trigger (Screen Tap)...")
        await TitanInteractionSuite.stabilize_environment(page)
        await page.mouse.click(10, 10)
        await asyncio.sleep(2)

        # 1. Visual Search for Thumbnail (Fuzzy Match)
        print("DEBUG: Searching for 'Spin da Bottle' in Lobby...")
        # Pure CSS + Playwright Fuzzy Match
        spin_bottle_sel = ":has-text('Spin da Bottle'), [alt*='Spin da Bottle'], .m-game-item:has-text('Spin')"
        try:
            thumbnail = page.locator(spin_bottle_sel).filter(visible=True).first
            await thumbnail.wait_for(state="visible", timeout=30000)
            print("DEBUG: Thumbnail found. Clicking to launch game...")
            await thumbnail.click(force=True)
        except Exception as e:
            print(f"WARNING: Could not find 'Spin da Bottle' in Lobby via visible locator: {e}")
            # Emergency JS click fallback
            await page.evaluate("""() => {
                const els = Array.from(document.querySelectorAll('*'));
                const target = els.find(e => e.innerText && e.innerText.includes('Spin da Bottle'));
                if (target) target.click();
            }""")

        # 2. Wait for Iframe to mount (60s Timeout)
        print("DEBUG: Waiting for Game Iframe to mount (60s)...")
        iframe_locator = page.frame_locator("iframe[src*='sportygames']")

        try:
            # Wait for container
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=60000)
            print("DEBUG: Iframe attached. Waiting for Canvas...")
        except:
            print("WARNING: Iframe attachment timed out. Stabilizing and retrying...")
            await TitanInteractionSuite.stabilize_environment(page)
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=30000)

        # 3. Wait for actual game UI
        ui_indicator = iframe_locator.locator("canvas, .history, .results, .history-list, .bet-panel").first
        try:
            await ui_indicator.wait_for(state="visible", timeout=60000)
            print("DEBUG: Game Engine hydrated.")
            return iframe_locator
        except Exception as e:
            print(f"CRITICAL: Game hydration failed: {e}")
            os.makedirs("artifacts", exist_ok=True)
            await page.screenshot(path="artifacts/game_load_failure.png")
            return iframe_locator

    async def run_environment(self, storage_state: Optional[Dict[str, Any]] = None):
        """Prepares a browser page with full Ghost Protocol stealth and UI sensitivity."""
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            viewport={'width': 390, 'height': 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale="en-GB",
            timezone_id="Africa/Lagos",
            permissions=["geolocation"],
            color_scheme="dark",
            storage_state=storage_state,
            ignore_https_errors=True,
            extra_http_headers={"x-platform": "WAP"}
        )

        page = await context.new_page()
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            Object.defineProperty(navigator, 'platform', {get: () => 'iPhone'});
        """)

        await TitanInteractionSuite.apply_ui_sensitivity(page)

        return pw, browser, context, page
