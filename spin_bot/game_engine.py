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
        """V5.51: Pure Native Playwright Interaction (Trusted Events Bypass)."""
        os.makedirs("artifacts", exist_ok=True)

        # 1. Native Landing & Stabilization
        print("DEBUG: Stage 1 - Navigating to Homepage...")
        await page.goto(self.game_url, wait_until="networkidle")
        await TitanInteractionSuite.stabilize_environment(page, delay_nuke=True)
        await page.screenshot(path="artifacts/telemetry_1_homepage.png")

        # 2. Native Hamburger Menu (Trusted Event)
        print("DEBUG: Stage 2 - Accessing Hamburger Menu (Hardware Emulation)...")
        menu_button = page.locator(".m-header-left, .icon-menu, [aria-label*='Menu'], .menu-icon, .icon-hamburger").first
        try:
            await menu_button.click(force=True, timeout=10000)
            await asyncio.sleep(2) # Wait for slide-out
        except Exception as e:
            print(f"WARNING: Menu button not found/clickable: {e}. Trying direct lobby jump as fallback...")
            await page.goto("https://www.football.com/ng/m/games", wait_until="networkidle")

        await page.screenshot(path="artifacts/telemetry_2_menu_open.png")

        # 3. Native Routing (Trusted Event)
        print("DEBUG: Stage 3 - Executing Native Route to Games...")
        games_link = page.locator("a:has-text('Games'), a:has-text('Casino'), a[href*='/games']").filter(visible=True).first
        try:
            if await games_link.count() > 0:
                await games_link.click(force=True)
                print("DEBUG: Games link clicked.")
            else:
                print("DEBUG: Games link not visible in menu, forcing navigation...")
                await page.goto("https://www.football.com/ng/m/games", wait_until="networkidle")
        except:
             await page.goto("https://www.football.com/ng/m/games", wait_until="networkidle")

        # 4. Wait for SPA Hydration
        print("DEBUG: Stage 4 - Waiting 8s for SPA Lobby Render...")
        await asyncio.sleep(8)
        await page.screenshot(path="artifacts/telemetry_3_lobby_grid.png")

        # 5. Native Hunter-Seeker (Hardware Scrolling + Trusted Click)
        print("DEBUG: Stage 5 - Native Hunter-Seeker (HREF-Targeting)...")
        await page.mouse.click(10, 10)
        for i in range(4):
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(1.5)

        await page.screenshot(path="artifacts/telemetry_4_lobby_scroll.png")

        # Use advanced locator for reliable game match
        game_target = page.locator("a[href*='spin'], img[alt*='spin'], img[src*='spin'], :has-text('Spin da Bottle'), .m-game-item:has-text('Spin')").first

        print("DEBUG: Stage 6 - Triggering Game Entry (Hardware Click)...")
        try:
            await game_target.click(force=True, timeout=15000)
        except Exception as e:
            print(f"WARNING: Native click failed: {e}. Executing Kernel Fallback...")
            await page.evaluate("window.location.href = '/ng/m/games/spin-da-bottle'")

        await asyncio.sleep(5)
        await page.screenshot(path="artifacts/telemetry_5_final_transition.png")

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
        """V5.51 Chimera Environment: Mixed Fingerprint Stealth."""
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
