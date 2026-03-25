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

        # V5.7 Network Discovery Buffer
        self.network_log = []

        # V5.3 Dynamic Endpoint Discovery
        self.endpoints = {
            "history": None,
            "bet": None,
            "balance": None
        }

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
                    "type": "REQUEST",
                    "url": request.url,
                    "method": method,
                    "headers": dict(request.headers),
                    "payload": post_data,
                    "timestamp": time.time()
                }
                self.network_log.append(entry)
                if "bet" in url and method == "POST":
                    self.endpoints["bet"] = normalize_url(request.url)
                elif any(x in url for x in ["history", "spins", "results", "orders"]):
                    self.endpoints["history"] = normalize_url(request.url)
                elif "balance" in url:
                    self.endpoints["balance"] = normalize_url(request.url)
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
                    "type": "RESPONSE",
                    "url": response.url,
                    "status": status,
                    "headers": dict(headers),
                    "response": body,
                    "timestamp": time.time()
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
        try:
            os.makedirs("artifacts", exist_ok=True)
            log_path = "artifacts/network_log.txt"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"--- OMNI V5.8 NETWORK AUDIT ({time.ctime()}) ---\n\n")
                for entry in self.network_log:
                    f.write(f"[{entry['type']}] {entry.get('method', '')} {entry['url']}\n")
                    f.write(f"Headers: {json.dumps(entry['headers'], indent=2)}\n")
                    if entry.get("payload"): f.write(f"Payload: {entry['payload']}\n")
                    if entry.get("response"): f.write(f"Response: {entry['response']}\n")
                    f.write("-" * 80 + "\n")
        except: pass

    async def login(self):
        user = os.getenv("FOOTBALL_NG_LOGIN")
        pw = os.getenv("FOOTBALL_NG_PASS")
        if not user or not pw: return
        print("DEBUG: Executing UI Login Flow...")
        try:
            await self.page.goto(self.login_url, wait_until="networkidle")
            await self.page.wait_for_selector("body")
            # Trigger modal
            try: await self.page.locator("text=Login").first.click(timeout=5000)
            except: await self.page.locator("button:has-text('Login')").click(timeout=5000)
            # Fill credentials
            await self.page.locator("input[type='text'], input[type='tel'], input[placeholder*='Mobile']").first.fill(user)
            await self.page.fill("input[type='password']", pw)
            await self.page.locator("button:has-text('Login')").last.click()
            await asyncio.sleep(random.uniform(5.0, 7.0))
        except Exception as e:
            print(f"DEBUG: Login UI Error: {e}")

    async def navigate_to_game_lobby(self):
        """V5.8 Pivot to /lobby architecture."""
        try:
            lobby_url = "https://www.football.com/ng/games/lobby"
            print(f"DEBUG: Navigating to Game Lobby -> {lobby_url}")
            await self.page.goto(lobby_url, wait_until="networkidle")
            await asyncio.sleep(random.uniform(2.0, 4.0))
        except: pass

    async def select_spin_game(self):
        """Specifically target 'Spin da Bottle' in the UI."""
        try:
            # Look for Spin da Bottle card
            candidates = await self.page.locator("div[class*='game'], a:has-text('Spin')").all()
            for cand in candidates:
                text = await cand.inner_text()
                if "spin" in text.lower():
                    await cand.scroll_into_view_if_needed()
                    await cand.click()
                    print("DEBUG: Spin da Bottle game selected.")
                    await asyncio.sleep(random.uniform(5.0, 8.0))
                    return True
        except: pass
        return False

    async def enable_one_tap_bet(self):
        """Activate 'One-Tap Bet' in game menu for seamless automation."""
        try:
            frame = self.page.frame_locator("iframe").first
            # Open menu (Ham)
            menu_trigger = frame.locator(".menu-trigger, .icon-menu, .ham-menu").first
            if await menu_trigger.is_visible():
                await menu_trigger.click()
                await asyncio.sleep(1)
                # Find One-Tap Bet toggle
                toggle = frame.locator("text='One-Tap Bet', .one-tap-bet").first
                if await toggle.is_visible():
                    await toggle.click()
                    print("DEBUG: One-Tap Bet ENABLED via UI.")
                    # Close menu
                    await menu_trigger.click()
        except: pass

    async def get_ui_history_bubbles(self) -> List[str]:
        """Scrapes history bar bubbles (UP/DOWN/MIDDLE)."""
        outcomes = []
        try:
            frame = self.page.frame_locator("iframe").first
            # Target color-coded or text-coded bubbles in history bar
            bubbles = await frame.locator(".history-item, .bubble, .result-item").all()
            for b in bubbles:
                text = (await b.inner_text()).strip().upper()
                if "UP" in text or "U" in text: outcomes.append("U")
                elif "DOWN" in text or "D" in text: outcomes.append("D")
                elif "MID" in text or "M" in text: outcomes.append("M")
            return outcomes[::-1] # Newest last
        except: pass
        return outcomes

    async def click_bet_button(self, direction: str):
        """Interacts directly with game action buttons."""
        try:
            frame = self.page.frame_locator("iframe").first
            selector = f"button:has-text('{direction}'), .{direction.lower()}-btn"
            target = frame.locator(selector).first
            if await target.is_visible():
                print(f"DEBUG: Placing UI Bet -> {direction}")
                await target.hover()
                await asyncio.sleep(random.uniform(0.5, 1.2))
                await target.click()
                await asyncio.sleep(random.uniform(2.0, 5.0)) # Anti-detection jitter
                return True
        except: pass
        return False

    async def close(self):
        try:
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except: pass
