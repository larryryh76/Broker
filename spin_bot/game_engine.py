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
        """V5.52: Splash-Screen Bypass & Strict Truth Gate (Phase 10)."""
        os.makedirs("artifacts", exist_ok=True)

        # 1. Truth Gate Stage 1 - Navigating to Homepage (No-Nuke Mode)
        print("DEBUG: Stage 1 - Navigating to Homepage (Wait for Splash)...")
        # Use domcontentloaded to avoid hanging on external ads
        await page.goto(self.game_url, wait_until="domcontentloaded")

        # Give the site 10 seconds to finish internal animations/handshakes
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
            print("SUCCESS: URL Transition Confirmed.")
        except Exception as e:
            print(f"CRITICAL: URL did not change! Stuck on loading page: {e}")
            await page.screenshot(path="artifacts/telemetry_failed_transition.png")
            # Emergency reload
            await page.reload(wait_until="networkidle")

        # 3. Truth Gate Stage 3 - Waiting for physical grid
        print("DEBUG: Stage 3 - Waiting for Grid Element to appear...")
        try:
            # Look for actual game items
            await page.wait_for_selector(".m-game-item, .game-item, .game-list", timeout=20000)
            print("SUCCESS: Game Grid detected.")
        except Exception:
            print("WARNING: Grid not detected. Site might be blank.")

        await page.screenshot(path="artifacts/telemetry_3_actual_lobby.png")

        # 4. Native Hunter-Seeker (Hardware Scrolling)
        print("DEBUG: Stage 4 - Native Hunter-Seeker (Coordinate Search)...")
        await page.mouse.click(10, 10)
        for i in range(4):
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(2)

        # 5. Phantom Tap Snipe (Coordinate-Based Native Click)
        # Advanced locator scan
        game_target = page.locator("a[href*='spin'], img[alt*='spin'], img[src*='spin'], :has-text('Spin')").first

        print("DEBUG: Stage 5 - Triggering Game Entry (Phantom Tap Snipe)...")
        try:
            if await game_target.is_visible():
                box = await game_target.bounding_box()
                if box:
                    # Move to center and click natively (Hardware level)
                    await page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                    print("DEBUG: Native Coordinate Click sent to 'Spin' icon.")
                else:
                    await game_target.click(force=True)
            else:
                print("DEBUG: Game target not visible, forcing Kernel Jump...")
                await page.evaluate("window.location.href = '/ng/m/games/spin-da-bottle'")
        except Exception as e:
            print(f"WARNING: Snipe failed: {e}. Executing Fallback...")
            await page.evaluate("window.location.href = '/ng/m/games/spin-da-bottle'")

        await asyncio.sleep(5)
        await page.screenshot(path="artifacts/telemetry_final_transition.png")

        # 6. Resilient Iframe Sync (60s)
        print("DEBUG: Waiting for Game Iframe (60s Resilience)...")
        iframe_locator = page.frame_locator("iframe[src*='sportygames']")

        try:
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=60000)
        except:
            await TitanInteractionSuite.stabilize_environment(page)
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=30000)

        # 7. Hydration Check
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
        """V5.52 Chimera Environment: Mixed Fingerprint Stealth."""
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
