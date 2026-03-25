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

        # V5.7 Network Discovery Buffer (Unified)
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

        # V5.7 FULL ASYNC NETWORK INTERCEPTION
        self.page.on("request", self._log_request)
        self.page.on("response", self._log_response)

        # FULL STEALTH
        if stealth:
            try:
                await stealth(self.page)
            except: pass

        await self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    async def _log_request(self, request: Request):
        """V5.7 Async Request Capture with Payload Extraction."""
        try:
            url = request.url.lower()
            # V5.7 Filter for critical reverse-engineering targets
            if any(x in url for x in ["game", "spin", "bet", "api", "order", "history", "result", "balance", "facts", "draw"]):
                method = request.method
                headers = request.headers
                post_data = None

                if method == "POST":
                    try:
                        post_data = request.post_data
                    except: pass

                entry = {
                    "type": "REQUEST",
                    "url": request.url,
                    "method": method,
                    "headers": dict(headers),
                    "payload": post_data,
                    "timestamp": time.time()
                }
                self.network_log.append(entry)

                print(f"DEBUG: Captured REQUEST -> {method} {request.url}")
                if post_data:
                    print(f"DEBUG: Payload captured: {str(post_data)[:100]}")

                # Discovery logic (Normalized)
                if "bet" in url and method == "POST":
                    self.endpoints["bet"] = normalize_url(request.url)
                elif any(x in url for x in ["history", "spins", "results", "orders"]):
                    self.endpoints["history"] = normalize_url(request.url)
                elif "balance" in url:
                    self.endpoints["balance"] = normalize_url(request.url)
        except: pass

    async def _log_response(self, response: Response):
        """V5.6 FORCE READ RAW RESPONSE BODY."""
        try:
            url = response.url.lower()
            if any(x in url for x in ["game", "spin", "bet", "api", "order", "history", "result", "balance", "facts", "draw"]):
                status = response.status
                headers = response.headers
                body = None

                # V5.6 Raw Byte Extraction
                try:
                    raw = await response.body()
                    if raw:
                        try:
                            if headers.get("content-encoding") == "gzip":
                                body = gzip.decompress(raw).decode("utf-8", errors="ignore")
                            else:
                                body = raw.decode("utf-8", errors="ignore")
                        except:
                            body = str(raw)
                except Exception as e:
                    print(f"DEBUG: Raw body read failed for {response.url}: {e}")

                # Size limit
                if body and len(body) > 2000:
                    body = body[:2000] + "... [TRUNCATED]"

                entry = {
                    "type": "RESPONSE",
                    "url": response.url,
                    "status": status,
                    "headers": dict(headers),
                    "response": body,
                    "timestamp": time.time()
                }
                self.network_log.append(entry)

                print(f"DEBUG: Captured response -> {response.url}")
                print(f"DEBUG: Sample -> {body[:200] if body else 'EMPTY'}")

                # V5.3/V5.4 Discovery Classifiers (Response-Based)
                if body:
                    raw_body = body.lower()
                    if any(x in raw_body for x in ["history", "results"]) and self.endpoints["history"] is None:
                        self.endpoints["history"] = normalize_url(response.url)
                    if any(x in raw_body for x in ["balance", "wallet"]) and self.endpoints["balance"] is None:
                        self.endpoints["balance"] = normalize_url(response.url)
        except Exception as e:
            print(f"DEBUG: Response intercept error: {e}")

    def save_network_logs(self):
        """V5.7 Human-Readable Text Log Persistence."""
        try:
            os.makedirs("artifacts", exist_ok=True)
            log_path = "artifacts/network_log.txt"

            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"--- OMNI V5.7 NETWORK INTELLIGENCE LOG (Generated: {time.ctime()}) ---\n\n")

                for entry in self.network_log:
                    f.write(f"[{entry['type']}] {entry.get('method', '')} {entry['url']}\n")
                    f.write(f"Timestamp: {entry['timestamp']}\n")

                    if "status" in entry:
                        f.write(f"Status: {entry['status']}\n")

                    f.write("Headers:\n")
                    for k, v in entry['headers'].items():
                        f.write(f"  {k}: {v}\n")

                    if entry.get("payload"):
                        f.write(f"Payload:\n{entry['payload']}\n")

                    if entry.get("response"):
                        f.write(f"Response:\n{entry['response']}\n")

                    f.write("-" * 80 + "\n\n")

            print(f"DEBUG: Human-readable intelligence saved to {log_path}")
        except Exception as e:
            print(f"DEBUG: Failed to save text logs: {e}")

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
        for i in range(3):
            try:
                await self.page.evaluate(trigger_script)
                await asyncio.sleep(5)
            except: pass

    async def _force_game_interaction(self):
        """V5.5 FORCE GAME ENGINE TO LOAD AND TRIGGER APIs."""
        print("DEBUG: Initiating Forced Game Engine Interaction (V5.5)...")
        try:
            frame = self.page.frame_locator("iframe").first
            try:
                await frame.locator("body").wait_for(timeout=15000)
            except: return

            await frame.locator("body").click(timeout=5000)
            selectors = ["button", ".start", ".play", ".spin", ".bet", ".start-btn", ".spin-btn"]
            for sel in selectors:
                try:
                    elements = await frame.locator(sel).all()
                    for el in elements:
                        if await el.is_visible():
                            await el.click(timeout=2000)
                            await asyncio.sleep(1)
                except: pass

            await frame.locator("body").click(position={"x": 300, "y": 400})
            await asyncio.sleep(5)
        except: pass

    async def navigate_to_spin_game(self):
        try:
            await self.page.goto(self.login_url, wait_until="networkidle", timeout=60000)
            await self.login()
            await asyncio.sleep(5)
            await self._trigger_active_discovery()

            candidates = await self.page.locator("div[class*='game'], .game-item, div:has-text('Spin')").all()
            for cand in candidates:
                try:
                    text = await cand.inner_text()
                    if "spin" in text.lower():
                        await cand.scroll_into_view_if_needed()
                        await cand.click()
                        await asyncio.sleep(10)
                        await self._force_game_interaction()
                        break
                except: continue

            print(f"DEBUG: V5.7 Discovery Traffic Triggered. Endpoints Found: {len([k for k,v in self.endpoints.items() if v])}")
        except Exception as e:
            print(f"DEBUG: Discovery Navigation Error: {e}")

    async def close(self):
        try:
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except: pass
