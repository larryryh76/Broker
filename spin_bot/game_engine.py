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
        # V5.57: Organic Front-Door Entry
        self.game_url = "https://www.football.com/ng/m/"

    async def get_frame(self, page: Page):
        """V5.57: Nuclear Hydration Bypass & Blind Navigation (Phase 17)."""
        os.makedirs("artifacts", exist_ok=True)

        # 1. Stage 2 - Forcing Entry
        print("DEBUG: Stage 2 - Forcing Entry (wait_until='commit')...")
        # We use 'commit' because 'networkidle' will never happen while loader is stuck
        await page.goto(self.game_url, wait_until="commit", timeout=60000)

        # Hard wait to let background scripts attempt to run
        print("DEBUG: Allowing 8s for background scripts to prime...")
        await asyncio.sleep(8)

        # 2. Stage 3 - Final Cleanup & Force Visibility
        print("DEBUG: Stage 3 - Executing Final Cleanup & Visibility Enforcement...")
        await page.evaluate("""() => {
            // 1. Delete anything still blocking the screen
            document.querySelectorAll('[class*="loading"], [id*="loading"], .m-loading-mask, .splash').forEach(el => el.remove());

            // 2. Force the App Container to show up
            const app = document.querySelector('#__nuxt') || document.querySelector('#app') || document.body;
            if (app) {
                app.style.display = 'block';
                app.style.visibility = 'visible';
                app.style.opacity = '1';
            }

            // 3. Prevent any "Loading" CSS from staying active
            document.documentElement.classList.remove('loading-active');
        }""")

        await page.screenshot(path="artifacts/telemetry_0_post_nuke.png")

        # 3. Stage 4 - Blind Navigation (Clicking what we can't see)
        print("DEBUG: Stage 4 - Executing Blind Navigation...")
        try:
            # We use force=True because the site might still think the loader is 'there'
            menu_btn = page.locator(".m-header-left, .icon-menu, .icon-hamburger").first
            await menu_btn.click(force=True, timeout=5000)
            print("DEBUG: Menu Clicked.")

            await asyncio.sleep(2)
            games_link = page.locator("text='Games', a[href*='/games']").first
            await games_link.click(force=True, timeout=5000)
            print("DEBUG: Games Link Clicked.")

            await asyncio.sleep(5)
        except Exception as e:
            print(f"WARNING: Native UI navigation failed: {e}. Executing Jump-Route...")
            await page.goto("https://www.football.com/ng/m/games", wait_until="commit")

        # 4. Stage 5 - Verifying Lobby Presence
        print("DEBUG: Stage 5 - Verifying Lobby Presence...")
        try:
            # If we get here and it's still loading, we kill the loader one last time
            await page.evaluate("() => { document.querySelectorAll('[class*=\"loading\"]').forEach(el => el.remove()); }")

            await page.wait_for_selector(".m-game-item, .game-item", timeout=15000)
            print("SUCCESS: Lobby Grid reached.")
            await page.screenshot(path="artifacts/telemetry_1_lobby_success.png")
        except Exception as e:
            print(f"CRITICAL: Failed to break the Loading Loop: {e}")
            await page.screenshot(path="artifacts/telemetry_1_final_fail.png", full_page=True)

        # 5. Final Stage - Native Hunter-Seeker (Coordinate Search)
        print("DEBUG: Final Stage - Initiating Target Snipe...")
        target = page.locator("a[href*='spin'], img[alt*='spin'], img[src*='spin'], :has-text('Spin')").first

        if await target.is_visible():
            box = await target.bounding_box()
            if box:
                # Perform native Ghost Touch
                await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=10)
                await asyncio.sleep(0.3)
                await page.mouse.down()
                await asyncio.sleep(0.15)
                await page.mouse.up()
                print("DEBUG: Native Snipe complete. Waiting for iframe...")
            else:
                await target.click(force=True)
        else:
             print("WARNING: Target not visible, forcing route fallback...")
             await page.goto("https://www.football.com/ng/m/games/spin-da-bottle", wait_until="commit")

        # 6. Resilient Iframe Sync (60s)
        print("DEBUG: Waiting for Game Iframe (60s Resilience)...")
        iframe_locator = page.frame_locator("iframe[src*='sportygames']")

        try:
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=60000)
            print("SUCCESS: Iframe mounted. Syncing hydration...")

            ui_indicator = iframe_locator.locator("canvas, .history, .results, .history-list, .bet-panel").first
            await ui_indicator.wait_for(state="visible", timeout=30000)
            print("DEBUG: Game Engine hydrated.")

            await page.screenshot(path="artifacts/telemetry_final_success.png")
            return iframe_locator
        except Exception as e:
            print(f"CRITICAL: Game hydration failed: {e}")
            await page.screenshot(path="artifacts/game_load_failure_final.png", full_page=True)
            return iframe_locator

    async def run_environment(self, storage_state: Optional[Dict[str, Any]] = None):
        """V5.57 Chimera Environment: Mixed Fingerprint + Nuclear Anti-Loader."""
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
        # V5.57: Phase 17 Anti-Loader MutationObserver
        await page.add_init_script("""
            const observer = new MutationObserver((mutations) => {
                for (const mutation of mutations) {
                    for (const node of mutation.addedNodes) {
                        if (node.nodeType === 1) {
                            if (node.classList.contains('m-loading-mask') ||
                                node.classList.contains('loading') ||
                                node.id.includes('loading') ||
                                node.innerHTML.includes('loading')) {
                                node.style.display = 'none';
                                node.remove();
                            }
                        }
                    }
                }
            });
            observer.observe(document.documentElement, { childList: true, subtree: true });
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
            Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
            Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
        """)

        await TitanInteractionSuite.apply_ui_sensitivity(page)

        return pw, browser, context, page
