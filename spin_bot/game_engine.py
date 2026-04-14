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
        self.game_url = "https://www.football.com/ng/m/"

    async def get_frame(self, page: Page):
        """V5.58: Gatekeeper & Mobile Lockdown (Phase 18)."""
        os.makedirs("artifacts", exist_ok=True)

        # 1. Front-Door Entry
        print("DEBUG: Stage 1 - Navigating to Homepage...")
        await page.goto(self.game_url, wait_until="commit", timeout=60000)

        # 2. THE GATEKEEPER GATE
        print("DEBUG: Stage 2 - Verification Gate Active...")
        gate_passed = False
        for attempt in range(5):
            if "/livescore" in page.url:
                print("WARNING: Redirected to Livescore. Forcing back...")
                await page.goto(self.game_url, wait_until="domcontentloaded")

            await page.evaluate("document.querySelectorAll('.m-loading-mask, [class*=\"loading\"]').forEach(el => el.remove())")

            healthy = page.locator(".m-header-main, .m-footer, .icon-home, .m-header-left").first
            if await healthy.is_visible():
                print("SUCCESS: Gate Passed.")
                gate_passed = True
                break
            await asyncio.sleep(5)

        if not gate_passed:
            print("CRITICAL: Gatekeeper Timeout. Nuclear Jump...")
            await page.goto("https://www.football.com/ng/m/games", wait_until="networkidle")

        # 3. Organic UI Navigation
        print("DEBUG: Stage 3 - Organic UI Navigation...")
        try:
            menu_btn = page.locator("i.icon-menu, .m-header-left, .icon-hamburger").first
            await menu_btn.click(force=True, timeout=10000)
            await asyncio.sleep(2)

            games_link = page.locator("text='Games', a[href*='/games']").first
            await games_link.click(force=True)
            await page.wait_for_selector(".m-game-item, .game-item", timeout=20000)
            print("SUCCESS: Lobby Grid reached.")
        except:
            await page.goto("https://www.football.com/ng/m/games", wait_until="commit")

        # 4. Target Snipe (Ghost Touch)
        print("DEBUG: Stage 4 - Target Snipe...")
        target = page.locator("a[href*='spin'], :has-text('Spin')").first
        if await target.is_visible():
            box = await target.bounding_box()
            if box:
                await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2, steps=10)
                await asyncio.sleep(0.3)
                await page.mouse.down()
                await asyncio.sleep(0.15)
                await page.mouse.up()
                print("DEBUG: Ghost Touch complete.")
            else: await target.click(force=True)
        else: await page.goto("https://www.football.com/ng/m/games/spin-da-bottle", wait_until="commit")

        # 5. Iframe Sync
        print("DEBUG: Stage 5 - Waiting for Iframe (60s)...")
        iframe_locator = page.frame_locator("iframe[src*='sportygames']")
        try:
            await page.locator("iframe[src*='sportygames']").wait_for(state="attached", timeout=60000)
            ui = iframe_locator.locator("canvas, .history, .results, .bet-panel").first
            await ui.wait_for(state="visible", timeout=60000)
            print("DEBUG: Game Engine hydrated.")
            return iframe_locator
        except Exception as e:
            print(f"CRITICAL: Hydration failed: {e}")
            await page.screenshot(path="artifacts/game_load_failure_final.png", full_page=True)
            return iframe_locator

    async def run_environment(self, storage_state: Optional[Dict[str, Any]] = None):
        """V5.58 Chimera Environment."""
        pw = await async_playwright().start()
        browser = await pw.chromium.launch(headless=True)
        iphone_13 = pw.devices['iPhone 13']
        context = await browser.new_context(
            **iphone_13,
            storage_state=storage_state,
            ignore_https_errors=True,
            extra_http_headers={"x-platform": "WAP"}
        )
        page = await context.new_page()
        # V5.57 Nuclear Anti-Loader
        await page.add_init_script("""
            const obs = new MutationObserver((muts) => {
                for (const m of muts) {
                    for (const n of m.addedNodes) {
                        if (n.nodeType === 1 && (n.classList.contains('m-loading-mask') || n.innerHTML.includes('loading'))) {
                            n.style.display = 'none'; n.remove();
                        }
                    }
                }
            });
            obs.observe(document.documentElement, { childList: true, subtree: true });
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
        """)
        await TitanInteractionSuite.apply_ui_sensitivity(page)
        return pw, browser, context, page
