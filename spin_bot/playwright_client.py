import os
import random
import asyncio
import time
import json
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

        # V5.1 Network Discovery Buffer
        self.network_log = []

        # V5.3 Dynamic Endpoint Discovery (Normalized)
        self.endpoints = {
            "history": None,
            "bet": None,
            "balance": None
        }

    async def setup(self):
        """Async initialization of the browser context."""
        self.playwright = await async_playwright().start()

        # REAL HUMAN CHROME USER AGENT
        REAL_CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

        # Hardened Launch Arguments
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

        self.browser = await self.playwright.chromium.launch(
            headless=True,
            args=launch_args,
            channel="chrome"
        )

        # Context Setup
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

        # V5.4 ASYNC NETWORK INTERCEPTION
        self.page.on("request", self._log_request)
        self.page.on("response", self._log_response)

        # FULL STEALTH
        if stealth:
            try:
                await stealth(self.page)
            except: pass

        await self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def _log_request(self, request: Request):
        try:
            url = request.url.lower()
            if any(x in url for x in ["game", "spin", "bet", "api", "order", "history", "result", "balance", "facts"]):
                entry = {
                    "type": "REQUEST",
                    "url": request.url,
                    "method": request.method,
                    "headers": dict(request.headers),
                    "post_data": request.post_data,
                    "timestamp": time.time()
                }
                self.network_log.append(entry)

                # Discovery logic
                if "bet" in url and request.method == "POST":
                    self.endpoints["bet"] = normalize_url(request.url)
                elif any(x in url for x in ["history", "spins", "results"]):
                    self.endpoints["history"] = normalize_url(request.url)
                elif "balance" in url:
                    self.endpoints["balance"] = normalize_url(request.url)
        except: pass

    async def _log_response(self, response: Response):
        """V5.4 Async Response Capture with Body Extraction."""
        try:
            url = response.url.lower()
            if any(x in url for x in ["game", "spin", "bet", "api", "order", "history", "result", "balance", "facts"]):
                content_type = response.headers.get("content-type", "").lower()
                body = None

                # V5.4 Explicit Async Content Capture
                try:
                    if "application/json" in content_type:
                        body = await response.json()
                    elif "text" in content_type:
                        body = await response.text()
                except Exception as e:
                    print(f"DEBUG: Failed to read response body for {response.url}: {e}")

                # Size limit
                body_str = str(body)
                if len(body_str) > 2000:
                    body_str = body_str[:2000] + "... [TRUNCATED]"

                entry = {
                    "type": "RESPONSE",
                    "url": response.url,
                    "status": response.status,
                    "headers": dict(response.headers),
                    "response": body_str,
                    "timestamp": time.time()
                }
                self.network_log.append(entry)

                print(f"DEBUG: Captured response -> {response.url}")
                print(f"DEBUG: Sample -> {body_str[:200]}")

                # V5.3/V5.4 Discovery Classifiers (Response-Based)
                if body:
                    raw_body = str(body).lower()
                    if any(x in raw_body for x in ["history", "results"]) and self.endpoints["history"] is None:
                        self.endpoints["history"] = normalize_url(response.url)
                    if any(x in raw_body for x in ["balance", "wallet"]) and self.endpoints["balance"] is None:
                        self.endpoints["balance"] = normalize_url(response.url)
        except Exception as e:
            print(f"DEBUG: Response intercept error: {e}")

    def save_network_logs(self):
        try:
            os.makedirs("artifacts", exist_ok=True)
            with open("artifacts/network_log.json", "w", encoding="utf-8") as f:
                json.dump(self.network_log, f, indent=2)
            print(f"DEBUG: V5.4 Discovery log saved with {len(self.network_log)} entries.")
        except: pass

    async def login(self):
        user = os.getenv("FOOTBALL_NG_LOGIN")
        pw = os.getenv("FOOTBALL_NG_PASS")
        if not user or not pw: return

        print("DEBUG: Initiating Login flow for discovery...")
        try:
            await self.page.wait_for_selector("body", timeout=15000)
            try:
                await self.page.locator("text=Login").first.click(timeout=5000)
            except:
                await self.page.locator("button:has-text('Login')").click(timeout=5000)

            await self.page.wait_for_selector("input[type='password']", timeout=15000)
            user_field = self.page.locator("input[type='text'], input[type='tel'], input[placeholder*='Mobile']").first
            await user_field.fill(user)
            await self.page.fill("input[type='password']", pw)
            await self.page.locator("button:has-text('Login')").last.click()
            await asyncio.sleep(7)
        except Exception as e:
            print(f"DEBUG: Login Error: {e}")
            raise e

    async def _trigger_active_discovery(self):
        """V5.1 FORCED API TRIGGER DISCOVERY."""
        print("DEBUG: Triggering Active Discovery via JS Injections...")

        trigger_script = """
        (async () => {
            try {
                // Common API endpoints
                const targets = [
                    '/api/ng/games/games-campaign/v1/campaign',
                    '/api/ng/orders/config/cutbet',
                    '/api/ng/factsCenter/flexiblebet/v2/getOddsKey',
                    '/api/ng/games/history',
                    '/api/ng/orders/history',
                    '/api/ng/bets/history',
                    '/api/ng/user/balance',
                    '/api/ng/results'
                ];

                for (const url of targets) {
                    try {
                        console.log("Triggering: " + url);
                        await fetch(url);
                        await new Promise(r => setTimeout(r, 1000));
                    } catch (e) {
                        console.log("Trigger error: " + url, e);
                    }
                }
            } catch (e) {
                console.log("Global trigger error:", e);
            }
        })();
        """

        # Retry loop for active discovery
        for i in range(3):
            print(f"DEBUG: Active Discovery Pass {i+1}/3...")
            try:
                await self.page.evaluate(trigger_script)
                await asyncio.sleep(5)
            except: pass

    async def navigate_to_spin_game(self):
        try:
            await self.page.goto(self.login_url, wait_until="networkidle", timeout=60000)
            await self.login()
            await asyncio.sleep(5)

            # V5.1 FORCE ACTIVE DISCOVERY
            await self._trigger_active_discovery()

            # Find and click the specific Spin game
            candidates = await self.page.locator("div[class*='game'], .game-item, div:has-text('Spin')").all()
            for cand in candidates:
                try:
                    text = await cand.inner_text()
                    if "spin" in text.lower():
                        await cand.scroll_into_view_if_needed()
                        await cand.click()
                        await asyncio.sleep(10)
                        break
                except: continue

            print(f"DEBUG: V5.4 Discovery Traffic Triggered. Endpoints Found: {len([k for k,v in self.endpoints.items() if v])}")
        except Exception as e:
            print(f"DEBUG: Discovery Navigation Error: {e}")

    async def close(self):
        try:
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except: pass
