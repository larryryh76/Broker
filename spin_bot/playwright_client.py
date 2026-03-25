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
        self.login_url = login_url
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.game_frame = None
        self.execution_log = []

        # V5.9 Target Metadata
        self.INDEPENDENT_LOGIN_URL = "https://www.football.com/ng/m/independent_login"

        # V5.7 Network Discovery Buffer
        self.network_log = []

        # V5.3 Dynamic Endpoint Discovery
        self.endpoints = {"history": None, "bet": None, "balance": None}

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
            if any(x in url for x in ["game", "spin", "bet", "api", "order", "history", "result", "balance", "facts", "draw"]):
                method = request.method
                post_data = request.post_data if method == "POST" else None
                entry = {
                    "type": "REQUEST", "url": request.url, "method": method,
                    "headers": dict(request.headers), "payload": post_data, "timestamp": time.time()
                }
                self.network_log.append(entry)
                if "bet" in url and method == "POST": self.endpoints["bet"] = normalize_url(request.url)
                elif any(x in url for x in ["history", "spins", "results", "orders"]): self.endpoints["history"] = normalize_url(request.url)
                elif "balance" in url: self.endpoints["balance"] = normalize_url(request.url)
        except: pass

    async def _log_response(self, response: Response):
        try:
            url = response.url.lower()
            if any(x in url for x in ["game", "spin", "bet", "api", "order", "history", "result", "balance", "facts", "draw"]):
                status = response.status
                headers = response.headers
                body = None
                try:
                    raw = await response.body()
                    if raw:
                        if headers.get("content-encoding") == "gzip":
                            body = gzip.decompress(raw).decode("utf-8", errors="ignore")
                        else:
                            body = raw.decode("utf-8", errors="ignore")
                except: pass
                if body and len(body) > 2000: body = body[:2000] + "... [TRUNCATED]"
                entry = {
                    "type": "RESPONSE", "url": response.url, "status": status,
                    "headers": dict(headers), "response": body, "timestamp": time.time()
                }
                self.network_log.append(entry)
                if body:
                    raw_body = body.lower()
                    if any(x in raw_body for x in ["history", "results"]) and self.endpoints["history"] is None:
                        self.endpoints["history"] = normalize_url(response.url)
                    if any(x in raw_body for x in ["balance", "wallet"]) and self.endpoints["balance"] is None:
                        self.endpoints["balance"] = normalize_url(response.url)
        except: pass

    def save_network_logs(self):
        """V5.9 Unified Human-Readable Execution and Network Audit."""
        try:
            os.makedirs("artifacts", exist_ok=True)
            log_path = "artifacts/execution_log.txt"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write("=== OMNI V5.9 EXECUTION AND INTELLIGENCE AUDIT ===\n\n")
                f.write("--- EXECUTION STEPS ---\n")
                for step in self.execution_log: f.write(f"{step}\n")
                f.write("\n" + "="*80 + "\n\n")
                f.write("--- NETWORK CAPTURE ---\n")
                for entry in self.network_log:
                    f.write(f"[{entry['type']}] {entry.get('method', '')} {entry['url']}\n")
                    if entry.get("payload"): f.write(f"Payload: {entry['payload']}\n")
                    if entry.get("response"): f.write(f"Response: {entry['response']}\n")
                    f.write("-" * 40 + "\n")
            self._log_execution(f"DEBUG: V5.9 Audit saved to {log_path}")
        except: pass

    async def login(self):
        user = os.getenv("FOOTBALL_NG_LOGIN")
        pw = os.getenv("FOOTBALL_NG_PASS")
        if not user or not pw: return

        self._log_execution(f"DEBUG: Bypassing pop-ups via direct login -> {self.INDEPENDENT_LOGIN_URL}")
        try:
            await self.page.goto(self.INDEPENDENT_LOGIN_URL, wait_until="networkidle")
            await self.page.wait_for_selector("input[type='password']", timeout=15000)

            user_field = self.page.locator("input[type='text'], input[type='tel'], input[placeholder*='Mobile']").first
            await user_field.fill(user)
            await self.page.fill("input[type='password']", pw)
            await self.page.locator("button:has-text('Login')").last.click()
            await asyncio.sleep(7)

            # V5.9 Handle Post-Login Overlays
            await self._handle_overlays()
            self._log_execution("DEBUG: Login Successful.")
        except Exception as e:
            self._log_execution(f"CRITICAL: Login UI Error: {e}")

    async def _handle_overlays(self):
        """V5.9 Close 'Download App' or 'Welcome' modals."""
        selectors = ["button.close-icon", ".modal-close", "[aria-label='Close']", ".close-btn"]
        for sel in selectors:
            try:
                btn = self.page.locator(sel).first
                if await btn.is_visible():
                    await btn.click(timeout=2000)
                    self._log_execution(f"DEBUG: Closed overlay via {sel}")
            except: pass

    async def _switch_to_game_frame(self) -> bool:
        """V5.9 Fix Game Access: The Iframe Issue."""
        try:
            self._log_execution("DEBUG: Searching for game iframe (sportygames)...")
            # Wait for frame element
            frame_element = await self.page.wait_for_selector('iframe[src*="sportygames"]', timeout=20000)
            if frame_element:
                self.game_frame = await frame_element.content_frame()
                self._log_execution("DEBUG: Switched to Game Frame.")
                return True
        except Exception as e:
            self._log_execution(f"DEBUG: Failed to find game frame: {e}")
        return False

    async def navigate_to_game_lobby(self):
        try:
            lobby_url = "https://www.football.com/ng/games/lobby"
            self._log_execution(f"DEBUG: Navigating to Game Lobby -> {lobby_url}")
            await self.page.goto(lobby_url, wait_until="networkidle")
            await self._handle_overlays()
        except: pass

    async def select_spin_game(self):
        try:
            candidates = await self.page.locator("div[class*='game'], a:has-text('Spin')").all()
            for cand in candidates:
                text = await cand.inner_text()
                if "spin" in text.lower():
                    await cand.scroll_into_view_if_needed()
                    await cand.click()
                    self._log_execution("DEBUG: Spin da Bottle game selected.")
                    await asyncio.sleep(10)
                    return await self._switch_to_game_frame()
        except: pass
        return False

    async def get_ui_history_bubbles(self) -> List[str]:
        """V5.9 History capture via .history_ball selector."""
        outcomes = []
        try:
            if not self.game_frame: return []
            # Target .history_ball within frame
            bubbles = await self.game_frame.locator(".history_ball").all()
            for b in bubbles:
                # Class or color detection
                cls = await b.get_attribute("class") or ""
                if "blue" in cls.lower(): outcomes.append("U")
                elif "red" in cls.lower(): outcomes.append("D")
                # Fallback to text
                else:
                    text = (await b.inner_text()).strip().upper()
                    if "UP" in text or "U" in text: outcomes.append("U")
                    elif "DOWN" in text or "D" in text: outcomes.append("D")
            return outcomes[::-1]
        except: pass
        return outcomes

    async def click_bet_button(self, direction: str, amount: float):
        """V5.9 Robust Text Locators for Betting."""
        try:
            if not self.game_frame: return False

            # 1. Fill Stake
            stake_input = self.game_frame.locator('input[type="number"]').first
            if await stake_input.is_visible():
                await stake_input.fill(str(amount))

            # 2. Click Directional Button (Text based)
            selector = "UP" if direction == "U" else "DOWN"
            target = self.game_frame.locator("button", has_text=selector).first

            if await target.is_visible():
                self._log_execution(f"DEBUG: Executing UI Bet -> {selector} (₦{amount})")
                await target.hover()
                await target.click()
                await asyncio.sleep(random.uniform(2.0, 5.0))
                return True
        except Exception as e:
            self._log_execution(f"DEBUG: Bet execution failed: {e}")
        return False

    async def close(self):
        try:
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except: pass
