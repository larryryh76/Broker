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
        # V5.50: Start at Homepage for Telemetry Stage 1
        self.game_url = "https://www.football.com/ng/m/"

    async def get_frame(self, page: Page):
        """V5.50: Ultimate Hunter-Seeker with Visual Telemetry."""
        os.makedirs("artifacts", exist_ok=True)

        # 1. Telemetry Stage 1: Homepage Landing
        print("DEBUG: Stage 1 - Navigating to Homepage...")
        await page.goto(self.game_url, wait_until="networkidle")
        await TitanInteractionSuite.stabilize_environment(page, delay_nuke=True)
        await page.screenshot(path="artifacts/telemetry_1_homepage.png")

        # 2. Telemetry Stage 2: Lobby Navigation (Kernel-Level)
        print("DEBUG: Stage 2 - Executing Kernel-Level Navigation to Lobby...")
        await page.evaluate("() => { window.location.href = '/ng/m/games'; }")
        await asyncio.sleep(5)
        await page.screenshot(path="artifacts/telemetry_2_post_nav.png")

        # 3. Telemetry Stage 3: API Grid Wait
        print("DEBUG: Stage 3 - Waiting 8s for API Grid Render...")
        await asyncio.sleep(8)
        await page.screenshot(path="artifacts/telemetry_3_api_ready.png")

        # 4. Telemetry Stage 4: Deep Scroll & Search
        print("DEBUG: Stage 4 - Deploying Ultimate Hunter-Seeker (HREF-Targeting)...")
        # Wake up render engine
        await page.mouse.click(10, 10)
        # Deep-scroll to wake lazy-loading
        for i in range(3):
            print(f"DEBUG: Scrolling Lobby (Pass {i+1}/3)...")
            await page.mouse.wheel(0, 1500)
            await asyncio.sleep(1.5)
        await page.screenshot(path="artifacts/telemetry_4_post_scroll.png")

        hunter_success = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('a, div, img, span, p, h3');
                for (let el of elements) {
                    let text = (el.innerText || '').toLowerCase();
                    let href = el.getAttribute('href') ? el.getAttribute('href').toLowerCase() : '';
                    if (!href && el.closest('a')) {
                        href = el.closest('a').getAttribute('href').toLowerCase();
                    }

                    // Lock onto anything containing 'spin' in text or link
                    if (text.includes('spin') || href.includes('spin')) {
                        let target = el.closest('a') || el;
                        console.log("DEBUG: Hunter-Seeker found target: " + href);
                        target.click();
                        return true;
                    }
                }
                // NUCLEAR FALLBACK: Force the Vue Router directly
                console.log("WARNING: DOM scan failed. Executing Nuclear Direct-Route...");
                window.location.href = "/ng/m/games/spin-da-bottle";
                return "NUCLEAR_TRIGGERED";
            }
        """)

        print(f"DEBUG: Hunter-Seeker Status: {hunter_success}")
        await asyncio.sleep(5)
        await page.screenshot(path="artifacts/telemetry_5_final_transition.png")

        # 5. Wait for Iframe to mount (60s Timeout)
        print("DEBUG: Waiting for Game Iframe to mount (60s)...")
        iframe_locator = page.frame_locator("iframe[src*='sportygames']")

        try:
            # Wait for container
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=60000)
            print("DEBUG: Iframe attached. Waiting for Canvas hydration...")
        except:
            print("WARNING: Iframe attachment timed out. Stabilizing and retrying...")
            await TitanInteractionSuite.stabilize_environment(page)
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=30000)

        # 6. Final Game UI Indicators
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
        """V5.50: Chimera Environment with Full Telemetry."""
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
