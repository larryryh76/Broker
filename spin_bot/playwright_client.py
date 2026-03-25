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
        self.login_url = "https://www.football.com" # RESET V3.0
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.game_frame = None
        self.execution_log = []

        # V5.7 Network Discovery Buffer
        self.network_log = []

    def _log_execution(self, message: str):
        print(message)
        self.execution_log.append(f"[{time.ctime()}] {message}")

    async def setup(self):
        self.playwright = await async_playwright().start()
        REAL_CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--window-position=0,0",
            "--headless=new",
            "--enable-javascript"
        ]
        self.browser = await self.playwright.chromium.launch(headless=True, args=launch_args, channel="chrome")
        self.context = await self.browser.new_context(
            java_script_enabled=True,
            user_agent=REAL_CHROME_UA,
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Africa/Lagos",
            geolocation={"latitude": 6.5244, "longitude": 3.3792},
            permissions=["geolocation"]
        )
        self.page = await self.context.new_page()
        self.page.set_default_timeout(60000)
        self.page.on("request", self._log_request)
        self.page.on("response", self._log_response)
        if stealth: await stealth(self.page)
        await self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    async def _log_request(self, request: Request):
        try:
            url = request.url.lower()
            if any(x in url for x in ["game", "spin", "bet", "api", "history", "draw"]):
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

    def save_cycle_logs(self):
        """V3.0 Alpha Plain Text Logging."""
        try:
            os.makedirs("artifacts", exist_ok=True)
            log_path = "artifacts/cycle_logs.txt"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("=== OMNI-RECURSIVE MONEY MACHINE V3.0 ALPHA LOG ===\n\n")
                f.write("--- EXECUTION ---\n")
                for step in self.execution_log: f.write(f"{step}\n")
                f.write("\n--- NETWORK INTELLIGENCE ---\n")
                for entry in self.network_log:
                    f.write(f"[{entry['type']}] {entry['url']}\n")
                    if entry.get("response"): f.write(f"Data: {entry['response'][:500]}\n")
            self._log_execution(f"DEBUG: V3.0 Logs persisted to {log_path}")
        except: pass

    async def login(self):
        user = os.getenv("FOOTBALL_NG_LOGIN")
        pw = os.getenv("FOOTBALL_NG_PASS")
        if not user or not pw: return

        self._log_execution(f"DEBUG: V3.0 Login Reset -> {self.login_url}")
        try:
            await self.page.goto(self.login_url, wait_until="networkidle")

            # Close overlays
            await self._handle_overlays()

            try: await self.page.locator("text=Login").first.click(timeout=5000)
            except: await self.page.locator("button:has-text('Login')").click(timeout=5000)

            # V3.0 Ambigious Locator Fix
            await self.page.locator("input[type='text'], input[type='tel']").first.fill(user)
            await self.page.locator("section >> input[type='password']").first.fill(pw)

            await self.page.locator("button:has-text('Login')").last.click()
            await asyncio.sleep(7)
            await self._handle_overlays()
        except Exception as e:
            self._log_execution(f"CRITICAL: V3.0 Login UI Error: {e}")

    async def _handle_overlays(self):
        selectors = ["button.close-icon", ".modal-close", "[aria-label='Close']", ".close-btn"]
        for sel in selectors:
            try:
                btn = self.page.locator(sel).first
                if await btn.is_visible(): await btn.click(timeout=2000)
            except: pass

    async def enter_game_environment(self) -> bool:
        """V3.0 Direct Navigation to Spin da Bottle."""
        try:
            lobby_url = "https://www.football.com/ng/games/lobby"
            await self.page.goto(lobby_url, wait_until="networkidle")

            candidates = await self.page.locator("div[class*='game'], a:has-text('Spin')").all()
            for cand in candidates:
                text = await cand.inner_text()
                if "spin" in text.lower():
                    await cand.click()
                    await asyncio.sleep(10)
                    # V3.0 Switch to Game Frame
                    self.game_frame = self.page.frame_locator("iframe[src*='sportygames']")
                    self._log_execution("DEBUG: Switched to Game Frame.")
                    return True
        except: pass
        return False

    async def capture_history_texts(self) -> List[str]:
        """V3.0 Result Capture from Iframe."""
        try:
            if not self.game_frame: return []
            # Feed the Brain
            items = await self.game_frame.locator(".history_ball").all_inner_texts()
            outcomes = []
            for text in items:
                t = text.strip().upper()
                if "UP" in t or "U" in t: outcomes.append("U")
                elif "DOWN" in t or "D" in t: outcomes.append("D")
                else: outcomes.append("M")
            return outcomes[::-1] # Newest last
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
