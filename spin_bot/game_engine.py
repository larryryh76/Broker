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
        # V5.55: Walk through the Front Door (Homepage)
        self.game_url = "https://www.football.com/ng/m/"

    async def get_frame(self, page: Page):
        """V5.55: Full Human Traversal (The Front Door)."""
        os.makedirs("artifacts", exist_ok=True)

        # 1. Stage 1 - Loading Homepage (The Front Door)
        print("DEBUG: Stage 1 - Loading Homepage (The Front Door)...")
        # Must start at root to allow cookies and Vue to initialize naturally
        await page.goto(self.game_url, wait_until="networkidle")
        # Give splash screen time to clear naturally
        print("DEBUG: Waiting 4s for Splash Screen to clear...")
        await asyncio.sleep(4)
        await page.screenshot(path="artifacts/telemetry_0_homepage.png")

        # 2. Stage 2 - Organic UI Navigation to Games
        print("DEBUG: Stage 2 - Organic UI Navigation to Games...")
        try:
            # Try to open hamburger menu
            menu_btn = page.locator(".m-header-left, .icon-menu, .icon-hamburger").first
            if await menu_btn.is_visible():
                await menu_btn.click(force=True)
                await asyncio.sleep(2) # Menu slide animation

            # Find and click 'Games' link natively via soft DOM click
            print("DEBUG: Executing soft DOM click on Games route...")
            await page.evaluate("""() => {
                const gameLink = document.querySelector('a[href*="/games"]');
                if(gameLink) gameLink.click();
            }""")
        except Exception as e:
            print(f"WARNING: Menu navigation snagged: {e}. Attempting direct lobby jump...")
            await page.goto("https://www.football.com/ng/m/games", wait_until="networkidle")

        # 3. Stage 3 - Waiting for Vue Hydration (Grid Load)
        print("DEBUG: Stage 3 - Waiting for Vue Hydration (Grid Load)...")
        try:
            # Wait for physical grid elements
            await page.wait_for_selector(".m-game-item, .game-item", timeout=20000)
            print("SUCCESS: Lobby Grid loaded organically!")
            await page.screenshot(path="artifacts/telemetry_1_lobby_success.png")
        except Exception as e:
            print("CRITICAL: Grid failed to load after organic nav. API might be blocking.")
            await page.screenshot(path="artifacts/telemetry_1_lobby_fail.png", full_page=True)

        # 4. Stage 4 - Ghost Touch Snipe
        print("DEBUG: Stage 4 - Ghost Touch Snipe...")
        # Find 'Spin da Bottle'
        target = page.locator("a:has-text('Spin'), div:has-text('Spin'), .m-game-item:has-text('Spin')").first

        if await target.is_visible():
            box = await target.bounding_box()
            if box:
                center_x = box['x'] + box['width'] / 2
                center_y = box['y'] + box['height'] / 2

                print(f"DEBUG: Executing Ghost Touch at X:{center_x}, Y:{center_y}")
                # Smooth movement + timed press (bypass isTrusted)
                await page.mouse.move(center_x, center_y, steps=15)
                await asyncio.sleep(0.3)
                await page.mouse.down()
                await asyncio.sleep(0.15) # Real tap duration
                await page.mouse.up()
                print("DEBUG: Tap complete. Waiting for iframe...")
            else:
                print("WARNING: Could not calculate box. Executing standard click.")
                await target.click(force=True)
        else:
            print("CRITICAL: Target 'Spin da Bottle' not found on screen.")

        # 5. Stage 5 - Waiting for SportyGames Iframe
        print("DEBUG: Stage 5 - Waiting for SportyGames Iframe (NO NUKING)...")
        iframe_locator = page.frame_locator("iframe[src*='sportygames']")

        try:
            # Patience wait for iframe mount
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=60000)
            print("SUCCESS: Iframe successfully mounted! We are in.")

            # Wait for internal hydration
            ui_indicator = iframe_locator.locator("canvas, .history, .results, .history-list, .bet-panel").first
            await ui_indicator.wait_for(state="visible", timeout=30000)
            print("DEBUG: Game Engine hydrated.")

            await page.screenshot(path="artifacts/telemetry_final_success.png")
            return iframe_locator
        except Exception as e:
            print(f"CRITICAL: Iframe failed to mount/hydrate: {e}")
            await page.screenshot(path="artifacts/telemetry_final_error.png", full_page=True)
            return iframe_locator

    async def run_environment(self, storage_state: Optional[Dict[str, Any]] = None):
        """V5.55 Chimera Environment: Mixed Fingerprint Stealth."""
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
