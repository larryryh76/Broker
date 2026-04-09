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
        """V5.30 Iframe Sync."""
        # Pre-emptive stabilization
        await TitanInteractionSuite.stabilize_environment(page)
        await TitanInteractionSuite.human_jiggle(page)

        game_frame = page.frame_locator("iframe[src*='sportygames']")
        ui_indicator = game_frame.locator("canvas, .history, .results, .history-list").first

        try:
            await ui_indicator.wait_for(state="visible", timeout=45000)
            print("DEBUG: Game Environment hydrated.")
            return game_frame
        except:
            print("WARNING: Game hydration timed out. Final Stabilize...")
            await TitanInteractionSuite.stabilize_environment(page)
            await ui_indicator.wait_for(state="visible", timeout=15000)
            return game_frame

    async def run_environment(self, storage_state: Optional[Dict[str, Any]] = None):
        """Prepares a browser page with full stealth and UI sensitivity."""
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)

        # Emulate iPhone 15 Fingerprint
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            viewport={'width': 390, 'height': 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            storage_state=storage_state,
            ignore_https_errors=True,
            extra_http_headers={"x-platform": "WAP"}
        )

        page = await context.new_page()
        await page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")

        # Inject V5.21 UI Suite
        await TitanInteractionSuite.apply_ui_sensitivity(page)

        return pw, browser, context, page
