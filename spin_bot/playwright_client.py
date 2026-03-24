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

class PlaywrightClient:
    def __init__(self, login_url: str):
        self.login_url = login_url
        self.playwright = sync_playwright().start()

        # V5.0 Network Interception Buffer
        self.network_log = []

        # V5.0 Dynamic Endpoint Discovery
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

        # V5.0 FULL NETWORK INTERCEPTION
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
            # Filter for relevant traffic
            if any(x in url for x in ["game", "spin", "bet", "api", "auth", "login", "history", "balance"]):
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

                # Discovery logic
                if "bet" in url and request.method == "POST":
                    self.endpoints["bet"] = request.url
                elif any(x in url for x in ["history", "spins"]):
                    self.endpoints["history"] = request.url
                elif "balance" in url:
                    self.endpoints["balance"] = request.url
        except: pass

    def _log_response(self, response: Response):
        try:
            url = response.url.lower()
            if any(x in url for x in ["game", "spin", "bet", "api", "auth", "login", "history"]):
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
        except: pass

    def save_network_logs(self):
        """V5.0 Consolidated Network Log Persistence."""
        try:
            os.makedirs("artifacts", exist_ok=True)
            with open("artifacts/network_log.json", "w", encoding="utf-8") as f:
                json.dump(self.network_log, f, indent=2)
            print(f"DEBUG: V5.0 Discovery log saved.")
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

    def navigate_to_spin_game(self):
        """V5.0 Advanced Navigation to trigger Discovery Traffic."""
        try:
            self.page.goto(self.login_url, wait_until="networkidle", timeout=60000)
            self.login()
            time.sleep(5)

            # 1. Look for Game/Spin sections
            for t in ["Spin", "Games", "Virtual", "Casino"]:
                try:
                    el = self.page.locator(f"text={t}").first
                    if el.is_visible():
                        el.click()
                        time.sleep(3)
                except: continue

            # 2. Find and click the specific Spin game
            candidates = self.page.locator("div[class*='game'], .game-item, div:has-text('Spin')").all()
            for cand in candidates:
                try:
                    if "spin" in cand.inner_text().lower():
                        cand.scroll_into_view_if_needed()
                        cand.click()
                        time.sleep(10) # Wait for game load and traffic
                        break
                except: continue

            print(f"DEBUG: Discovery Traffic Triggered. Endpoints Found: {len([k for k,v in self.endpoints.items() if v])}")
        except Exception as e:
            print(f"DEBUG: Discovery Navigation Error: {e}")

    def close(self):
        try:
            self.browser.close()
            self.playwright.stop()
        except: pass
