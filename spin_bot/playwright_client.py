import os
import random
import time
import json
from playwright.sync_api import sync_playwright, Page, ElementHandle, Response, Request, WebSocket
try:
    from playwright_stealth import stealth
except ImportError:
    stealth = None
from typing import List, Optional, Dict, Union
from spin_bot.api_client import normalize_url

class PlaywrightClient:
    def __init__(self, login_url: str):
        self.login_url = login_url
        self.playwright = sync_playwright().start()

        # V5.1 Network Discovery Buffer
        self.network_log = []

        # V5.3 Dynamic Endpoint Discovery (Normalized)
        self.endpoints = {
            "history": None,
            "bet": None,
            "balance": None
        }

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

        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=launch_args,
            channel="chrome"
        )

        # Context Setup
        self.context = self.browser.new_context(
            java_script_enabled=True,
            user_agent=REAL_CHROME_UA,
            viewport={"width": 1366, "height": 768},
            locale="en-US",
            timezone_id="Africa/Lagos",
            geolocation={"latitude": 6.5244, "longitude": 3.3792},
            permissions=["geolocation"]
        )

        self.page = self.context.new_page()
        self.page.set_default_timeout(60000)

        # V5.1 FULL NETWORK INTERCEPTION
        self.page.on("request", self._log_request)
        self.page.on("response", self._log_response)

        # FULL STEALTH
        if stealth:
            try:
                stealth(self.page)
            except: pass

        self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def _log_request(self, request: Request):
        try:
            url = request.url.lower()
            # V5.1 Broadened Capture Filter
            if any(x in url for x in ["game", "spin", "bet", "api", "order", "history", "result", "balance", "facts"]):
                entry = {
                    "type": "REQUEST",
                    "url": request.url,
                    "method": request.method,
                    "headers": dict(request.headers),
                    "post_data": request.post_data,
                    "cookies": self.context.cookies(request.url),
                    "timestamp": time.time()
                }
                self.network_log.append(entry)

                # V5.3 Discovery Logic (Normalized)
                if "bet" in url and request.method == "POST":
                    self.endpoints["bet"] = normalize_url(request.url)
                elif any(x in url for x in ["history", "spins", "results"]):
                    self.endpoints["history"] = normalize_url(request.url)
                elif "balance" in url:
                    self.endpoints["balance"] = normalize_url(request.url)
        except: pass

    def _log_response(self, response: Response):
        try:
            url = response.url.lower()
            if any(x in url for x in ["game", "spin", "bet", "api", "order", "history", "result", "balance", "facts"]):
                content_type = response.headers.get("content-type", "").lower()
                body = None
                if "application/json" in content_type:
                    try:
                        body = response.json()
                    except: pass

                entry = {
                    "type": "RESPONSE",
                    "url": response.url,
                    "status": response.status,
                    "headers": dict(response.headers),
                    "body": body,
                    "timestamp": time.time()
                }
                self.network_log.append(entry)

                # V5.3 Discovery Classifiers (Normalized)
                if body:
                    raw_body = str(body).lower()
                    if any(x in raw_body for x in ["history", "results"]) and self.endpoints["history"] is None:
                        self.endpoints["history"] = normalize_url(response.url)
                    if any(x in raw_body for x in ["balance", "wallet"]) and self.endpoints["balance"] is None:
                        self.endpoints["balance"] = normalize_url(response.url)
        except: pass

    def save_network_logs(self):
        """V5.1 Consolidated Network Log Persistence."""
        try:
            os.makedirs("artifacts", exist_ok=True)
            with open("artifacts/network_log.json", "w", encoding="utf-8") as f:
                json.dump(self.network_log, f, indent=2)
            print(f"DEBUG: V5.1 Discovery log saved.")
        except: pass

    def login(self):
        user = os.getenv("FOOTBALL_NG_LOGIN")
        pw = os.getenv("FOOTBALL_NG_PASS")
        if not user or not pw: return

        print("DEBUG: Initiating Login flow for discovery...")
        try:
            self.page.wait_for_selector("body", timeout=15000)
            try:
                self.page.locator("text=Login").first.click(timeout=5000)
            except:
                self.page.locator("button:has-text('Login')").click(timeout=5000)

            self.page.wait_for_selector("input[type='password']", timeout=15000)
            user_field = self.page.locator("input[type='text'], input[type='tel'], input[placeholder*='Mobile']").first
            user_field.fill(user)
            self.page.fill("input[type='password']", pw)
            self.page.locator("button:has-text('Login')").last.click()
            time.sleep(7)
        except Exception as e:
            print(f"DEBUG: Login Error: {e}")
            raise e

    def _trigger_active_discovery(self):
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
                self.page.evaluate(trigger_script)
                time.sleep(5)
            except: pass

    def navigate_to_spin_game(self):
        """V5.1 Advanced Navigation and Discovery."""
        try:
            self.page.goto(self.login_url, wait_until="networkidle", timeout=60000)
            self.login()
            time.sleep(5)

            # V5.1 FORCE ACTIVE DISCOVERY
            self._trigger_active_discovery()

            # Find and click the specific Spin game
            candidates = self.page.locator("div[class*='game'], .game-item, div:has-text('Spin')").all()
            for cand in candidates:
                try:
                    if "spin" in cand.inner_text().lower():
                        cand.scroll_into_view_if_needed()
                        cand.click()
                        time.sleep(10)
                        break
                except: continue

            print(f"DEBUG: V5.3 Discovery Traffic Triggered. Endpoints Found: {len([k for k,v in self.endpoints.items() if v])}")
        except Exception as e:
            print(f"DEBUG: Discovery Navigation Error: {e}")

    def close(self):
        try:
            self.browser.close()
            self.playwright.stop()
        except: pass
