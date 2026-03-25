import os
import random
import asyncio
import time
import json
import gzip
from playwright.async_api import async_playwright, Page, ElementHandle, Response, Request, WebSocket
try:
    from playwright_stealth import stealth_async as stealth
except ImportError:
    stealth = None
from typing import List, Optional, Dict, Union
from spin_bot.api_client import normalize_url

class PlaywrightClient:
    def __init__(self, login_url: str):
        self.login_url = "https://www.football.com"
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.game_frame = None
        self.execution_log = []
        self.network_log = []

    def _log_execution(self, message: str):
        print(message)
        self.execution_log.append(f"[{time.ctime()}] {message}")

    async def setup(self, cookies: List[Dict] = None):
        self.playwright = await async_playwright().start()

        # V3.0 MOBILE/HEADLESS STEALTH
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--headless=new"
        ]

        self.browser = await self.playwright.chromium.launch(headless=True, args=launch_args)

        # High-Fidelity iPhone 13 Emulation
        IPHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1"
        iphone_13 = self.playwright.devices["iPhone 13"]

        self.context = await self.browser.new_context(
            **iphone_13,
            user_agent=IPHONE_UA,
            locale="en-US",
            timezone_id="Africa/Lagos"
        )

        if cookies:
            await self.context.add_cookies(cookies)
            self._log_execution("DEBUG: Persistent session cookies injected.")

        self.page = await self.context.new_page()
        self.page.set_default_timeout(60000)
        self.page.on("request", self._log_request)
        self.page.on("response", self._log_response)

        # EMERGENCY REPAIR: Stealth before navigation
        if stealth:
            try:
                await stealth(self.page)
                self._log_execution("DEBUG: Playwright-Stealth activated.")
            except: pass
        await self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    async def _log_request(self, request: Request):
        try:
            url = request.url.lower()
            if any(x in url for x in ["game", "spin", "bet", "api", "history"]):
                entry = {"type": "REQUEST", "url": request.url, "method": request.method, "timestamp": time.time()}
                self.network_log.append(entry)
        except: pass

    async def _log_response(self, response: Response):
        try:
            url = response.url.lower()
            if any(x in url for x in ["game", "spin", "bet", "api", "history"]):
                body = None
                try:
                    raw = await response.body()
                    body = raw.decode("utf-8", errors="ignore")
                except: pass
                entry = {"type": "RESPONSE", "url": response.url, "response": body, "timestamp": time.time()}
                self.network_log.append(entry)
        except: pass

    def save_cycle_logs(self, confidence: float, spins: int):
        try:
            os.makedirs("artifacts", exist_ok=True)
            log_path = "artifacts/cycle_logs.txt"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"=== OMNI MACHINE V3.0 ACCURACY AUDIT ===\n")
                f.write(f"STATE UPDATED: {spins} spins recorded. Confidence: {confidence*100:.1f}%\n")
                f.write("-" * 30 + "\n\n")
                f.write("--- EXECUTION STEPS ---\n")
                for step in self.execution_log: f.write(f"{step}\n")
        except: pass

    async def login(self):
        user = os.getenv("FOOTBALL_NG_LOGIN")
        pw = os.getenv("FOOTBALL_NG_PASS")
        if not user or not pw: return

        self._log_execution(f"DEBUG: Redirecting for UI login...")
        try:
            await self.page.goto(self.login_url, wait_until="networkidle")
            await self._handle_overlays()

            try:
                await self.page.click("text=More", timeout=5000)
                await asyncio.sleep(2)
                await self.page.click("text=Login / Register", timeout=5000)
            except:
                try: await self.page.locator("button.m-login-button, .m-btn-full").first.click(timeout=5000)
                except: pass

            # V3.0 Ambiguous Locator Fix
            await self.page.locator("input[placeholder*='Mobile']").first.fill(user)
            await self.page.locator("input[type='password']").first.fill(pw)

            # SUBMIT
            await self.page.locator("button[type='submit'], .m-login-button").first.click()
            await asyncio.sleep(random.uniform(4.0, 6.0))
            await self._handle_overlays()

        except Exception as e:
            self._log_execution(f"CRITICAL: Login UI Error: {e}")
            await self.page.screenshot(path="artifacts/error.png")

    async def _handle_overlays(self):
        """EMERGENCY REPAIR: Recursive overlay check with forced clicks."""
        selectors = ["button.close-icon", ".modal-close", "[aria-label='Close']", ".close-btn"]
        for sel in selectors:
            try:
                # Use recursive check to clear multiple layers
                while True:
                    btn = self.page.locator(sel).first
                    if await btn.is_visible():
                        self._log_execution(f"DEBUG: Clearing overlay layer ({sel})")
                        await btn.click(timeout=2000, force=True) # Bypass invisible overlays
                        await asyncio.sleep(1)
                    else:
                        break
            except: pass

    async def navigate_to_game(self) -> bool:
        """V3.0 Refined Iframe & Navigation."""
        try:
            lobby_url = "https://www.football.com/ng/games/lobby"
            await self.page.goto(lobby_url, wait_until="networkidle")
            await self._handle_overlays()

            candidates = await self.page.locator("div[class*='game'], a:has-text('Spin')").all()
            for cand in candidates:
                text = await cand.inner_text()
                if "spin" in text.lower():
                    await cand.click()
                    await asyncio.sleep(5)

                    # EMERGENCY REPAIR: Explicit Wait for Iframe
                    self._log_execution("DEBUG: Waiting for SportyGames iframe...")
                    await self.page.wait_for_selector("iframe[src*='sportygames']", state="visible", timeout=30000)

                    # V3.0 Switch to Game Frame
                    self.game_frame = self.page.frame_locator("iframe[src*='sportygames']")
                    # Ensure frame internal state is ready
                    await self.game_frame.locator(".history_ball").first.wait_for(timeout=20000)
                    self._log_execution("DEBUG: Switched to Game Frame (SportyGames).")
                    return True
        except Exception as e:
            self._log_execution(f"DEBUG: Navigation Error: {e}")
        return False

    async def capture_history_texts(self) -> List[str]:
        """V3.0 Scraping Fix: Target .history_ball."""
        try:
            if not self.game_frame: return []
            items = await self.game_frame.locator(".history_ball").all_inner_texts()
            outcomes = []
            for text in items:
                t = text.strip().upper()
                if "UP" in t or "U" in t: outcomes.append("U")
                elif "DOWN" in t or "D" in t: outcomes.append("D")
                else: outcomes.append("M")
            return outcomes[::-1]
        except: pass
        return []

    async def place_ui_bet(self, direction: str, amount: float):
        """EMERGENCY REPAIR: Text-based button selectors."""
        try:
            if not self.game_frame: return False
            stake_input = self.game_frame.locator('input[type="number"]').first
            await stake_input.fill(str(amount))

            # Use specific button text mapping
            target_text = "UP" if direction == "U" else "DOWN"
            target = self.game_frame.locator("button", has_text=target_text).first

            await target.hover()
            await target.click(force=True)
            await asyncio.sleep(random.uniform(2.5, 6.8))
            return True
        except: return False

    async def get_session_cookies(self):
        return await self.context.cookies()

    async def close(self):
        try:
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except: pass
