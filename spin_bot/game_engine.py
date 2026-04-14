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
        # V5.58: Organic Front-Door Entry
        self.game_url = "https://www.football.com/ng/m/"

    async def get_frame(self, page: Page):
        """V5.58: Gatekeeper & Mobile Lockdown (Phase 18)."""
        os.makedirs("artifacts", exist_ok=True)

        # 1. Stage 1 - Navigating to Homepage
        print("DEBUG: Stage 1 - Forcing Mobile Entry...")
        await page.goto(self.game_url, wait_until="commit", timeout=60000)

        # 2. Stage 2 - THE GATEKEEPER GATE (Retry loop)
        print("DEBUG: Stage 2 - Verification Gate Active...")
        gate_passed = False
        for attempt in range(5):
            print(f"DEBUG: Verification Attempt {attempt+1}/5...")

            # Check for malicious redirect
            if "/livescore" in page.url:
                print("WARNING: Redirected to Livescore. Forcing back to Mobile...")
                await page.goto(self.game_url, wait_until="domcontentloaded")

            # Pre-emptive strike on loading mask
            await page.evaluate("document.querySelectorAll('.m-loading-mask, [class*=\"loading\"]').forEach(el => el.remove())")

            # Check for "Healthy" mobile elements
            healthy_element = page.locator(".m-header-main, .m-footer, .icon-home, .m-header-left").first
            if await healthy_element.is_visible():
                print("SUCCESS: Gate Passed. Mobile UI is rendered.")
                gate_passed = True
                break

            await asyncio.sleep(5)

        if not gate_passed:
            print("CRITICAL: Gatekeeper Timeout. Attempting Nuclear Jump...")
            await page.goto("https://www.football.com/ng/m/games", wait_until="networkidle")

        await page.screenshot(path="artifacts/telemetry_gatekeeper_check.png")

        # 3. Stage 3 - Organic UI Navigation
        print("DEBUG: Stage 3 - Executing Organic Navigation...")
        try:
            # Broad menu search
            menu_btn = page.locator("i.icon-menu, .m-header-left, .icon-hamburger, .menu-icon").first
            await menu_btn.click(force=True, timeout=10000)
            await asyncio.sleep(2)

            # Native click on Games
            games_link = page.locator("text='Games', a[href*='/games']").first
            await games_link.click(force=True, timeout=10000)
            print("DEBUG: Navigating to Games...")

            # Confirm grid visibility
            await page.wait_for_selector(".m-game-item, .game-item, .game-list", timeout=20000)
            print("SUCCESS: Grid confirmed.")
        except Exception as e:
            print(f"WARNING: Organic nav snagged: {e}. Executing fallback...")
            await page.goto("https://www.football.com/ng/m/games", wait_until="commit")

        await page.screenshot(path="artifacts/telemetry_lobby_check.png")

        # 4. Stage 4 - Target Snipe (Phantom Tap)
        print("DEBUG: Stage 4 - Initiating Target Snipe...")
        target = page.locator("a[href*='spin'], img[alt*='spin'], img[src*='spin'], :has-text('Spin')").first

        if await target.is_visible():
            box = await target.bounding_box()
            if box:
                # Perform native Ghost Touch (steps for human mimicry)
                await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=12)
                await asyncio.sleep(0.3)
                await page.mouse.down()
                await asyncio.sleep(0.15)
                await page.mouse.up()
                print("DEBUG: Native Snipe complete.")
            else:
                await target.click(force=True)
        else:
             print("WARNING: Target invisible, forcing jump...")
             await page.goto("https://www.football.com/ng/m/games/spin-da-bottle", wait_until="commit")

        # 5. Resilient Iframe Sync (60s)
        print("DEBUG: Stage 5 - Waiting for Game Iframe (60s Resilience)...")
        iframe_locator = page.frame_locator("iframe[src*='sportygames']")

        try:
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=60000)
            ui_indicator = iframe_locator.locator("canvas, .history, .results, .history-list, .bet-panel").first
            await ui_indicator.wait_for(state="visible", timeout=30000)
            print("DEBUG: Game Engine hydrated.")
            await page.screenshot(path="artifacts/telemetry_final_success.png")
            return iframe_locator
        except Exception as e:
            print(f"CRITICAL: Hydration failed: {e}")
            await page.screenshot(path="artifacts/game_load_failure_final.png", full_page=True)
            return iframe_locator

    async def run_environment(self, storage_state: Optional[Dict[str, Any]] = None):
        """V5.58 Gatekeeper Environment: iPhone 13 Emulation + Anti-Loader."""
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)

        # V5.58: Use Playwright's iPhone 13 device profile
        iphone_13 = pw.devices['iPhone 13']
        context = await browser.new_context(
            **iphone_13,
            storage_state=storage_state,
            ignore_https_errors=True,
            extra_http_headers={"x-platform": "WAP"}
        )

        page = await context.new_page()
        # Pre-emptive Anti-Loader strike
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
        """)

        await TitanInteractionSuite.apply_ui_sensitivity(page)

        return pw, browser, context, page
