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
        self.game_url = "https://www.football.com/ng/m/games/spin-da-bottle"

    async def get_frame(self, page: Page):
        """V5.44: High-Resilience Iframe Sync & WebGL Render Trigger."""
        print("DEBUG: Executing Render-Trigger (Screen Tap)...")
        # Pre-emptive stabilization
        await TitanInteractionSuite.stabilize_environment(page)
        # Simulate a physical screen tap to wake up the render engine (WebKit requirement)
        await page.mouse.click(10, 10)
        await asyncio.sleep(2)

        # Expanded Timeouts for heavy casino assets (V5.44)
        print("DEBUG: Waiting for Game Iframe (60s timeout)...")
        iframe_locator = page.frame_locator("iframe[src*='sportygames']")

        # Wait for iframe container to be attached first
        try:
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=60000)
            print("DEBUG: Game Iframe attached. Waiting for Canvas hydration...")
        except Exception as e:
            print(f"WARNING: Game Iframe attachment failed: {e}")
            # Final attempt after stabilizing
            await TitanInteractionSuite.stabilize_environment(page)
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=30000)

        # Wait for actual game UI indicators inside the frame
        ui_indicator = iframe_locator.locator("canvas, .history, .results, .history-list, .bet-panel").first
        try:
            await ui_indicator.wait_for(state="visible", timeout=60000)
            print("DEBUG: Game Environment hydrated and visible.")
            return iframe_locator
        except Exception as e:
            print(f"WARNING: Game UI hydration timed out: {e}. Attempting final rescue...")
            await TitanInteractionSuite.stabilize_environment(page)
            await ui_indicator.wait_for(state="visible", timeout=20000)
            return iframe_locator

    async def run_environment(self, storage_state: Optional[Dict[str, Any]] = None):
        """Prepares a browser page with full Ghost Protocol stealth and UI sensitivity."""
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)

        # V5.44: Full-Spectrum Cloaking Fingerprint (Ghost Protocol)
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
        # V5.44 Anti-Detection Lockdown
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            Object.defineProperty(navigator, 'platform', {get: () => 'iPhone'});
        """)

        # Inject V5.21 UI Suite
        await TitanInteractionSuite.apply_ui_sensitivity(page)

        return pw, browser, context, page
