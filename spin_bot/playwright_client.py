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

    async def setup(self):
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
        self.context = await self.browser.new_context(**iphone_13, locale="en-US", timezone_id="Africa/Lagos")
        self.page = await self.context.new_page()
        self.page.set_default_timeout(60000)
        self.page.on("request", self._log_request)
        self.page.on("response", self._log_response)
        if stealth:
            try:
                await stealth(self.page)
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

        # 1. BYPASS HOMEPAGE SEQUENCE
        self._log_execution(f"DEBUG: V3.0 Login Sequence -> {self.login_url}")
        try:
            # User Prompt: page.goto("https://www.football.com", wait_until="networkidle")
            await self.page.goto("https://www.football.com", wait_until="networkidle")
            await self._handle_overlays()

            try: await self.page.locator("text=Login").first.click(timeout=5000)
            except:
                try: await self.page.locator("button:has-text('Login')").click(timeout=5000)
                except: pass

            # 2. HANDLE MULTIPLE INPUTS (Strict User Prompt Selectors)
            await self.page.locator("input[type='tel'], input[placeholder*='Mobile']").first.fill(user)
            await self.page.locator("input[type='password']").first.fill(pw)

            # SUBMIT
            await self.page.locator("button[type='submit'], .m-login-button").first.click()
            await asyncio.sleep(7)
            await self._handle_overlays()
        except Exception as e:
            self._log_execution(f"CRITICAL: Login UI Error: {e}")
            await self.page.screenshot(path="artifacts/error.png")

    async def _handle_overlays(self):
        selectors = ["button.close-icon", ".modal-close", "[aria-label='Close']", ".close-btn"]
        for sel in selectors:
            try:
                btn = self.page.locator(sel).first
                if await btn.is_visible(): await btn.click(timeout=2000)
            except: pass

    async def navigate_to_game(self) -> bool:
        """V3.0 Pattern Detection Access."""
        try:
            # User Prompt: Go to: 'https://www.football.com'
            await self.page.goto("https://www.football.com", wait_until="networkidle")
            await asyncio.sleep(5)

            # If not directly on main page, try lobby
            if not await self.page.locator("iframe[src*='sportygames']").count():
                 await self.page.goto("https://www.football.com/ng/games/lobby", wait_until="networkidle")

            # Switch to Iframe
            self.game_frame = self.page.frame_locator("iframe[src*='sportygames']")
            self._log_execution("DEBUG: Switched to Game Frame.")
            return True
        except: pass
        return False

    async def capture_history_texts(self) -> List[str]:
        """V3.0 Scrape History."""
        try:
            if not self.game_frame: return []
            # User Prompt: Use 'frame.locator(".history_ball").all_inner_texts()'
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
            target = self.game_frame.locator("button", has_text="UP" if direction == "U" else "DOWN").first
            await target.click()
            await asyncio.sleep(random.uniform(2.0, 5.0))
            return True
        except: return False

    async def close(self):
        try:
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except: pass
