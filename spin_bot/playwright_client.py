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

        # V4.9 Network Analysis Buffers
        self.captured_requests = []
        self.captured_responses = []
        self.ws_urls = []

        # V4.9 Target Endpoints (Discovery Mode)
        self.BET_ENDPOINT = None
        self.SPIN_ENDPOINT = None

        # REAL HUMAN CHROME USER AGENT
        REAL_CHROME_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

        # Hardened Launch Arguments (Forcing modern headless shell)
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

        # Context Setup with Lagos Metadata
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

        # Enable Browser Console Logging
        self.page.on("console", lambda msg: print(f"BROWSER CONSOLE [{msg.type}]: {msg.text}"))

        # 1. ENABLE FULL NETWORK INTERCEPTION
        self.page.on("request", self._log_request)
        self.page.on("response", self._log_response)
        self.page.on("websocket", self._log_ws)

        # FULL STEALTH
        if stealth:
            try:
                stealth(self.page)
                print("DEBUG: Full Stealth Applied.")
            except: pass

        self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def _log_request(self, request: Request):
        try:
            url = request.url.lower()
            if any(x in url for x in ["game", "spin", "bet", "campaign", "socket", "api"]):
                data = {
                    "url": request.url,
                    "method": request.method,
                    "headers": request.headers,
                    "post_data": request.post_data,
                    "timestamp": time.time()
                }
                self.captured_requests.append(data)

                if "bet" in url:
                    self.BET_ENDPOINT = request.url
                    print(f"DEBUG: FOUND BET ENDPOINT: {request.url}")
                elif any(x in url for x in ["history", "spin"]):
                    self.SPIN_ENDPOINT = request.url
                    print(f"DEBUG: FOUND SPIN ENDPOINT: {request.url}")
        except: pass

    def _log_response(self, response: Response):
        try:
            content_type = response.headers.get("content-type", "").lower()
            if "application/json" in content_type:
                try:
                    body = response.json()
                    data = {
                        "url": response.url,
                        "status": response.status,
                        "data": body,
                        "timestamp": time.time()
                    }
                    self.captured_responses.append(data)
                except: pass
        except: pass

    def _log_ws(self, ws: WebSocket):
        print(f"DEBUG: WebSocket opened: {ws.url}")
        self.ws_urls.append(ws.url)

    def save_network_logs(self):
        """Persists captured network intelligence to artifacts."""
        try:
            os.makedirs("artifacts", exist_ok=True)

            with open("artifacts/network_requests.json", "w", encoding="utf-8") as f:
                json.dump(self.captured_requests, f, indent=2)

            with open("artifacts/network_responses.json", "w", encoding="utf-8") as f:
                json.dump(self.captured_responses, f, indent=2)

            print("DEBUG: Network Intelligence persisted to artifacts/.")
        except Exception as e:
            print(f"DEBUG: Failed to save network logs: {e}")

    def get_active_context(self) -> Union[Page, 'FrameLocator']:
        """V4.3 Iframe Handling."""
        try:
            iframes = self.page.query_selector_all("iframe")
            for frame in iframes:
                src = frame.get_attribute("src") or ""
                if "game" in src.lower() or "spin" in src.lower():
                    print(f"DEBUG: Game detected inside iframe: {src}")
                    return self.page.frame_locator(f"iframe[src*='{src}']")
        except: pass
        return self.page

    def login(self):
        """Robust Modal-Based Login Logic."""
        user = os.getenv("FOOTBALL_NG_LOGIN")
        pw = os.getenv("FOOTBALL_NG_PASS")
        if not user or not pw: return

        print("DEBUG: Initiating Login flow...")
        try:
            # V4.9 Human Delay before interaction
            time.sleep(random.uniform(2.0, 5.0))
            self.page.wait_for_selector("body", timeout=15000)

            try:
                for t in ["Accept", "Allow", "Agree"]:
                    btn = self.page.locator(f"text={t}").first
                    if btn.is_visible(): btn.click()
            except: pass

            try:
                self.page.locator("text=Login").first.click(timeout=5000)
            except:
                self.page.locator("button:has-text('Login')").click(timeout=5000)

            self.page.wait_for_selector("input[type='password']", timeout=15000)
            time.sleep(random.uniform(1.5, 3.0))

            user_field = self.page.locator("input[type='text'], input[type='tel'], input[placeholder*='Mobile']").first
            user_field.fill(user)
            self.page.fill("input[type='password']", pw)

            self.page.locator("button:has-text('Login')").last.click()

            time.sleep(7)
            if self.page.locator("text=Login").first.is_visible():
                raise Exception("Login Verification FAILED.")
            print("DEBUG: LOGIN SUCCESSFUL.")
        except Exception as e:
            print(f"DEBUG: Login Error: {e}")
            self.take_screenshot("login_failure")
            raise e

    def navigate_to_spin_game(self):
        """V4.9 Anti-Detection SPA Navigation."""
        max_page_retries = 2

        for p_attempt in range(max_page_retries + 1):
            try:
                print(f"DEBUG: Navigation Attempt {p_attempt + 1}...")
                self.page.goto(self.login_url, wait_until="networkidle", timeout=60000)

                # V4.8 Wait for full DOM hydration
                try:
                    self.page.wait_for_function("() => document.querySelectorAll('*').length > 1000", timeout=30000)
                    print(f"DEBUG: DOM hydrated. Node count: {len(self.page.locator('*').all())}")
                except:
                    print("WARNING: DOM hydration function timed out.")

                if p_attempt == 0: self.login()

                time.sleep(random.uniform(3.0, 6.0))

                # Proactive Block Detection
                if "Please turn JavaScript on" in self.page.content():
                    print("CRITICAL: JS RUNTIME FAILURE DETECTED.")
                    self.take_screenshot("js_failure")
                    raise Exception("JS DISABLED")

                self._unlock_ui()

                candidates = self.page.locator("a, button, div[class*='card'], div[class*='game']").all()
                matches = []
                for el in candidates:
                    try:
                        if not el.is_visible(): continue
                        text = el.inner_text().strip().lower()
                        rank = 0
                        if "spin da bottle" in text: rank = 3
                        elif "spin" in text and "bottle" in text: rank = 2
                        elif "spin" in text: rank = 1
                        if rank > 0: matches.append({"element": el, "text": text, "rank": rank})
                    except: continue

                matches.sort(key=lambda x: x["rank"], reverse=True)
                for match in matches:
                    el = match["element"]
                    try:
                        el.scroll_into_view_if_needed()
                        time.sleep(random.uniform(1.0, 2.0))
                        box = el.bounding_box()
                        if box:
                            self.page.mouse.click(box['x'] + box['width']/2, box['y'] + box['height']/2)
                        else: el.click()

                        time.sleep(5)
                        ctx = self.get_active_context()
                        for sel in ["div[class*='history']", "button:has-text('UP')", "canvas"]:
                            try:
                                if ctx.locator(sel).first.is_visible():
                                    print(f"DEBUG: Game environment VALIDATED via: {sel}")
                                    return
                            except: continue
                    except: continue

                if p_attempt < max_page_retries: self.page.reload()
            except Exception as e:
                print(f"DEBUG: Navigation error: {e}")

        self.take_screenshot("navigation_failure")
        self.dump_dom("navigation_failure_dom")
        raise Exception("V4.9 NAVIGATION FAILED.")

    def extract_from_network(self) -> List[str]:
        """Multi-Source Intelligence: XHR + WebSocket."""
        outcomes = []
        for packet in reversed(self.captured_responses):
            data = packet["data"]
            try:
                if isinstance(data, dict):
                    val = data.get("result") or data.get("outcome")
                    if val: outcomes.append(str(val).upper()[0])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, str) and item.upper() in ["U", "D"]:
                            outcomes.append(item.upper()[0])
                if outcomes: break
            except: continue
        return outcomes

    def detect_repeating_patterns(self) -> List[str]:
        """Hardened DOM Scraper."""
        ctx = self.get_active_context()
        for sel in ["div[class*='history']", "span:has-text('UP')", "xpath=//div[contains(@class,'item')][1]"]:
            try:
                elements = ctx.locator(sel).all()
                if elements:
                    outcomes = []
                    for el in elements:
                        text = el.inner_text().strip().upper()
                        if "UP" in text or "U" in text: outcomes.append("U")
                        elif "DOWN" in text or "D" in text: outcomes.append("D")
                    if outcomes: return outcomes
            except: continue
        return []

    def detect_betting_elements(self) -> Dict[str, Optional[ElementHandle]]:
        """Identify interaction points."""
        ctx = self.get_active_context()
        res = {"up": None, "down": None, "amount": None}
        try:
            res["up"] = ctx.locator("button:has-text('UP'), button:has-text('BUY'), .up-btn").first
            res["down"] = ctx.locator("button:has-text('DOWN'), button:has-text('SELL'), .down-btn").first
            res["amount"] = ctx.locator("input[type='number'], input[placeholder*='Bet']").first
        except: pass
        return res

    def take_screenshot(self, name: str):
        try:
            os.makedirs("artifacts", exist_ok=True)
            self.page.screenshot(path=f"artifacts/{name}_{int(time.time())}.png")
        except: pass

    def _unlock_ui(self) -> bool:
        """V4.6 Pre-Navigation Unlock."""
        triggers = ["AZ", "Menu", "Games", "Lobby"]
        pre_count = len(self.page.locator("*").all())
        for t in triggers:
            try:
                selector = f"text={t}, button:has-text('{t}')"
                el = self.page.locator(selector).first
                if el.is_visible():
                    el.scroll_into_view_if_needed()
                    time.sleep(random.uniform(0.5, 1.5))
                    el.click()
                    time.sleep(5)
                    if len(self.page.locator("*").all()) > pre_count: return True
            except: continue
        return False

    def dump_dom(self, name: str):
        try:
            os.makedirs("artifacts", exist_ok=True)
            with open(f"artifacts/{name}.html", "w", encoding="utf-8") as f:
                f.write(self.page.content())
        except: pass

    def close(self):
        try:
            self.browser.close()
            self.playwright.stop()
        except: pass
