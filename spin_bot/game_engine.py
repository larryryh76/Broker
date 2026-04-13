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
        # V5.54: Target Lobby directly with Zero-Nuke Strategy
        self.game_url = "https://www.football.com/ng/m/games"

    async def get_frame(self, page: Page):
        """V5.54: Zero-Interference (Ghost Touch) Entry."""
        os.makedirs("artifacts", exist_ok=True)

        # 1. Stage 1 - Direct Organic Entry (Zero-Nuke)
        print("DEBUG: Stage 1 - Direct Organic Entry (Zero-Nuke)...")
        # Go straight to games, let site load naturally
        await page.goto(self.game_url, wait_until="networkidle")

        # Let hydration finish naturally
        print("DEBUG: Waiting 6s for API to populate grid naturally...")
        await asyncio.sleep(6)
        await page.screenshot(path="artifacts/telemetry_1_lobby_check.png")

        # 2. Stage 2 - Verifying Grid & Target
        print("DEBUG: Stage 2 - Verifying Grid & Target...")
        # Use fuzzy search for target without altering DOM
        game_box = page.locator(".m-game-item, .game-item, a:has-text('Spin'), div:has-text('Spin')").first

        if await game_box.is_visible():
            print("SUCCESS: Target spotted. Initiating Ghost Touch Snipe...")
            box = await game_box.bounding_box()
            if box:
                center_x = box['x'] + box['width'] / 2
                center_y = box['y'] + box['height'] / 2

                # Smooth, human-like mouse movement and click
                await page.mouse.move(center_x, center_y, steps=10)
                await asyncio.sleep(0.2)
                await page.mouse.down()
                await asyncio.sleep(0.15) # Real finger press duration
                await page.mouse.up()
                print("DEBUG: Ghost Touch Executed. Waiting for game to mount...")
            else:
                print("WARNING: Bounding box failed. Executing standard organic click.")
                await game_box.click(force=True)
        else:
            print("CRITICAL: Grid failed to load natively. Check telemetry_1.")

        # 3. Stage 3: Wait for the iframe naturally
        print("DEBUG: Stage 3 - Waiting for SportyGames Iframe (NO NUKING)...")
        iframe_locator = page.frame_locator("iframe[src*='sportygames']")

        try:
            # Patients wait for attachment
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=60000)
            print("SUCCESS: Iframe successfully mounted! We are in.")

            # Wait for internal hydration
            ui_indicator = iframe_locator.locator("canvas, .history, .results, .history-list, .bet-panel").first
            await ui_indicator.wait_for(state="visible", timeout=60000)
            print("DEBUG: Game Engine hydrated.")

            await page.screenshot(path="artifacts/telemetry_final_success.png")
            return iframe_locator
        except Exception as e:
            print(f"CRITICAL: Iframe failed to mount/hydrate: {e}")
            await page.screenshot(path="artifacts/telemetry_final_error.png", full_page=True)
            return iframe_locator

    async def run_environment(self, storage_state: Optional[Dict[str, Any]] = None):
        """V5.54 Chimera Environment: Mixed Fingerprint Stealth."""
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
