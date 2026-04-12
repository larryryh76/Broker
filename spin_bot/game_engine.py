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
        # V5.50: Start at Homepage for Organic Navigation
        self.game_url = "https://www.football.com/ng/m/"

    async def get_frame(self, page: Page):
        """V5.53: SPA Deadlock Breaker & Truth Gate (Phase 11)."""
        os.makedirs("artifacts", exist_ok=True)

        # 1. Truth Gate Stage 1 - Navigating to Homepage
        print("DEBUG: Stage 1 - Navigating to Homepage (Wait for Splash)...")
        await page.goto(self.game_url, wait_until="domcontentloaded")
        print("DEBUG: Waiting 10s for Splash Screen to clear...")
        await asyncio.sleep(10)
        await page.screenshot(path="artifacts/telemetry_1_homepage.png")

        # 2. Truth Gate Stage 2 - Forcing Route to Lobby
        print("DEBUG: Stage 2 - Forcing Route to Lobby...")
        await page.evaluate("() => { window.location.href = '/ng/m/games'; }")

        try:
            # TRUTH GATE: Confirm physical URL transition
            print("DEBUG: Waiting for URL transition to /games...")
            await page.wait_for_url("**/games**", timeout=20000)
            print("SUCCESS: URL Transitioned. Framework is likely frozen.")

            # THE DEADLOCK BREAKER: Force a hard refresh of the page
            print("DEBUG: Executing Hard Refresh to break SPA Deadlock...")
            await page.reload(wait_until="domcontentloaded")
            await asyncio.sleep(5) # Give it 5 seconds to rebuild the DOM

        except Exception as e:
            print(f"CRITICAL: URL did not change! Stuck on loading page: {e}")
            await page.screenshot(path="artifacts/telemetry_failed_transition.png")
            # Emergency reload anyway
            await page.reload(wait_until="networkidle")

        # 3. Truth Gate Stage 3 - Waiting for physical grid
        print("DEBUG: Stage 3 - Waiting for Grid Element to appear...")
        try:
            # We now wait up to 20 seconds for the actual API to populate the grid
            await page.wait_for_selector(".m-game-item, .game-item, .game-list, a[href*='spin']", timeout=20000)
            print("SUCCESS: Game Grid detected after Hard Refresh.")
        except Exception:
            print("WARNING: Grid STILL not detected. API might be blocking our IP.")

        await page.screenshot(path="artifacts/telemetry_3_actual_lobby.png")

        # 4. Stage 4: Direct URL Force (Nuclear Fallback)
        print("DEBUG: Stage 4 - Direct URL Force (Nuclear Fallback)...")
        # Since we know the lobby is unstable, immediately try to hard-load the game directly
        try:
            await page.goto("https://www.football.com/ng/m/games/spin-da-bottle", wait_until="domcontentloaded")
            await asyncio.sleep(8)
        except Exception as e:
            print(f"WARNING: Direct load interrupted: {e}")

        await page.screenshot(path="artifacts/telemetry_final_transition.png")

        # 5. Resilient Iframe Sync (60s)
        print("DEBUG: Waiting for Game Iframe (60s Resilience)...")
        iframe_locator = page.frame_locator("iframe[src*='sportygames']")

        try:
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=60000)
        except:
            await TitanInteractionSuite.stabilize_environment(page)
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=30000)

        # 6. Hydration Check
        ui_indicator = iframe_locator.locator("canvas, .history, .results, .history-list, .bet-panel").first
        try:
            await ui_indicator.wait_for(state="visible", timeout=60000)
            print("DEBUG: Game Engine hydrated.")
            return iframe_locator
        except Exception as e:
            print(f"CRITICAL: Game hydration failed: {e}")
            await page.screenshot(path="artifacts/game_load_failure_final.png")
            return iframe_locator

    async def run_environment(self, storage_state: Optional[Dict[str, Any]] = None):
        """V5.53 Chimera Environment: Mixed Fingerprint Stealth."""
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)

        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={'width': 375, 'height': 812},
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
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        """)

        await TitanInteractionSuite.apply_ui_sensitivity(page)

        return pw, browser, context, page
