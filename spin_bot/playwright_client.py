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
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--headless=new"
        ]
        self.browser = await self.playwright.chromium.launch(headless=True, args=launch_args)
        iphone_13 = self.playwright.devices["iPhone 13"]
        iphone_13['viewport'] = {'width': 390, 'height': 844}
        self.context = await self.browser.new_context(**iphone_13, locale="en-NG", timezone_id="Africa/Lagos")
        if cookies: await self.context.add_cookies(cookies)
        self.page = await self.context.new_page()
        self.page.set_default_timeout(60000)
        self.page.on("request", self._log_request)
        self.page.on("response", self._log_response)
        if stealth:
            try: await stealth(self.page)
            except: pass
        await self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    async def _handle_regional_splash(self):
        """V5.9.3: Close region select or confirm buttons."""
        selectors = ["text=Nigeria", "text=Confirm", "button:has-text('Nigeria')", ".region-confirm"]
        for sel in selectors:
            try:
                el = self.page.locator(sel).first
                if await el.is_visible():
                    await el.click(timeout=3000)
                    self._log_execution(f"DEBUG: Selected Region via {sel}")
            except: pass

    async def _navigate_via_bottom_menu(self):
        """V5.9.3: Fallback navigation via Bottom Menu."""
        try:
            self._log_execution("DEBUG: Attempting Bottom Menu navigation fallback...")
            await self.page.locator("text=More").click(timeout=10000)
            await asyncio.sleep(2)
            await self.page.locator("text=Games").click(timeout=10000)
            await asyncio.sleep(5)
        except Exception as e:
            self._log_execution(f"DEBUG: Bottom menu navigation failed: {e}")

    async def login(self):
        user = os.getenv("FOOTBALL_NG_LOGIN")
        pw = os.getenv("FOOTBALL_NG_PASS")
        if not user or not pw: return
        self._log_execution(f"DEBUG: Initializing Aggressive Login sequence...")
        try:
            # V5.9.3: wait_until="commit" to bypass redirects
            await self.page.goto(self.login_url, wait_until="commit")
            await self._handle_regional_splash()
            await self._handle_overlays()

            login_triggers = ["a[href*='login']", ".m-login-btn", "text=Login", "text=More"]
            for trigger in login_triggers:
                try:
                    el = self.page.locator(trigger).first
                    if await el.is_visible():
                        await el.click(timeout=5000)
                        await asyncio.sleep(2)
                        break
                except: pass

            try:
                btn = self.page.locator("text=Login / Register").first
                if await btn.is_visible(): await btn.click()
            except: pass

            await self.page.locator("input[placeholder*='Mobile']").first.fill(user)
            await self.page.locator("input[type='password']").first.fill(pw)
            await self.page.locator("button[type='submit'], .m-login-button").first.click()
            await asyncio.sleep(7)
            await self._handle_overlays()
        except Exception as e:
            self._log_execution(f"CRITICAL: Login UI Error: {e}")
            await self.page.screenshot(path="artifacts/error.png")

    async def navigate_to_game(self) -> bool:
        try:
            lobby_url = "https://www.football.com/ng/games/lobby"
            await self.page.goto(lobby_url, wait_until="networkidle")
            await self._handle_overlays()

            # V5.9.3: Fix Selector Syntax
            self._log_execution("DEBUG: Waiting for Game Lobby hydration...")
            try:
                await self.page.wait_for_selector(".game-item, :text('Spin da Bottle')", timeout=30000)
            except:
                await self._navigate_via_bottom_menu()

            candidates = await self.page.locator("div[class*='game'], a:has-text('Spin')").all()
            for cand in candidates:
                text = await cand.inner_text()
                if "spin" in text.lower():
                    await cand.click()
                    await asyncio.sleep(5)
                    await self.page.wait_for_selector("iframe[src*='sportygames']", state="visible", timeout=30000)
                    self.game_frame = self.page.frame_locator("iframe[src*='sportygames']")
                    await self.game_frame.locator(".history_ball").first.wait_for(timeout=20000)
                    self._log_execution("DEBUG: Landed in Gaming Environment.")
                    return True
        except Exception as e:
            self._log_execution(f"DEBUG: Navigation Error: {e}")
        return False

    async def _handle_overlays(self):
        selectors = ["button.close-icon", ".modal-close", "[aria-label='Close']", ".close-btn"]
        for sel in selectors:
            try:
                while True:
                    btn = self.page.locator(sel).first
                    if await btn.is_visible():
                        await btn.click(timeout=2000, force=True)
                        await asyncio.sleep(1)
                    else: break
            except: pass

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

    async def capture_history_texts(self) -> List[str]:
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
        try:
            if not self.game_frame: return False
            stake_input = self.game_frame.locator('input[type="number"]').first
            await stake_input.fill(str(amount))
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
