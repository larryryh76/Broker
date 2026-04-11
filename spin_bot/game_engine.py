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
        # V5.49: Target Homepage first for handshake
        self.game_url = "https://www.football.com/ng/m/"

    async def get_frame(self, page: Page):
        """V5.49: Advanced DOM Routing with Kernel-Level Fallback."""
        # 1. Front-Door Entry: Navigate to Homepage
        print("DEBUG: Navigating to Homepage (V5.49 Handshake)...")
        await asyncio.sleep(random.uniform(2, 5))
        await page.goto(self.game_url, wait_until="networkidle")
        await TitanInteractionSuite.stabilize_environment(page, delay_nuke=True)

        # 2. Advanced DOM Router Bypass
        print("DEBUG: Executing Advanced DOM Router Bypass...")
        nav_clicked = await page.evaluate("""
            () => {
                const links = document.querySelectorAll('a');
                for (let link of links) {
                    let href = (link.getAttribute('href') || '').toLowerCase();
                    let text = (link.innerText || '').trim().toLowerCase();
                    if (href.includes('/games') || href.includes('/casino') || text === 'games' || text === 'casino' || text === 'mini games') {
                        console.log("DEBUG: Found routing link! Href: " + href);
                        link.click();
                        return true;
                    }
                }
                return false;
            }
        """)

        # 3. Kernel-Level Routing Fallback
        if not nav_clicked:
            print("DEBUG: UI Link hidden. Executing Kernel-Level Navigation...")
            try:
                await page.evaluate("window.location.href = '/ng/m/games'")
                await asyncio.sleep(5)
                nav_clicked = True # Signal that we attempted navigation
            except Exception as e:
                print(f"DEBUG: Kernel-Level Routing failed: {e}")

        if not nav_clicked:
            print("WARNING: Complete failure to route to Games lobby.")
            os.makedirs("artifacts", exist_ok=True)
            await page.screenshot(path="artifacts/final_routing_failure.png", full_page=True)
        else:
            print("DEBUG: Routed to Lobby. Waiting for render...")
            await asyncio.sleep(random.uniform(4, 6))

        # 4. Aggressive Hunter-Seeker Search
        print("DEBUG: Deploying Hunter-Seeker JS...")
        await page.mouse.click(10, 10)

        for i in range(3):
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(1.5)

        hunter_success = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('a, div, img, span, p, h3');
                for (let el of elements) {
                    let text = (el.innerText || '').toLowerCase();
                    let alt = (el.getAttribute('alt') || '').toLowerCase();
                    let src = (el.getAttribute('src') || '').toLowerCase();

                    if (text.includes('spin') || alt.includes('spin') || src.includes('spin')) {
                        let target = el;
                        const parentLink = el.closest('a');
                        if (parentLink) target = parentLink;
                        target.click();
                        return true;
                    }
                }
                return false;
            }
        """)

        if not hunter_success:
            print("WARNING: Hunter-Seeker failed. Artifact rescue...")
            os.makedirs("artifacts", exist_ok=True)
            await page.screenshot(path="artifacts/lobby_failed_search.png", full_page=True)

        # 5. Resilient Iframe Wait (60s)
        print("DEBUG: Waiting for Game Iframe (60s Resilience)...")
        iframe_locator = page.frame_locator("iframe[src*='sportygames']")

        try:
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=60000)
        except:
            await TitanInteractionSuite.stabilize_environment(page, delay_nuke=True)
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=30000)

        # 6. Hydration Check
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
        """V5.49 Chimera Environment: Mixed Fingerprint Stealth."""
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
