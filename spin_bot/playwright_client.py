import os
import random
import time
import json
from playwright.sync_api import sync_playwright, Page, ElementHandle, Response, WebSocket
from typing import List, Optional, Dict, Union

class PlaywrightClient:
    def __init__(self, login_url: str):
        self.login_url = login_url
        self.playwright = sync_playwright().start()

        # V4.3 Intelligence Buffers
        self.network_responses = []
        self.ws_messages = []

        # Hardened Launch Arguments
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--window-position=0,0"
        ]

        self.browser = self.playwright.chromium.launch(
            headless=True,
            args=launch_args
        )

        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )

        self.page = self.context.new_page()

        # Activate Interceptors BEFORE navigation
        self.page.on("response", self._handle_response)
        self.page.on("websocket", self._handle_ws)

        self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    def _handle_response(self, response: Response):
        try:
            url = response.url.lower()
            if any(x in url for x in ["spin", "result", "game", "round", "history"]):
                try:
                    body = response.json()
                    self.network_responses.append({"url": url, "data": body, "timestamp": time.time()})
                except: pass
        except: pass

    def _handle_ws(self, ws: WebSocket):
        print(f"DEBUG: WebSocket opened: {ws.url}")
        ws.on("frame_received", lambda payload: self._parse_ws_message(payload))

    def _parse_ws_message(self, payload):
        try:
            # Check if payload is string and looks like JSON
            if isinstance(payload, str) and ("{" in payload):
                data = json.loads(payload)
                self.ws_messages.append({"data": data, "timestamp": time.time()})
        except: pass

    def get_active_context(self) -> Union[Page, 'FrameLocator']:
        """V4.3 Iframe Handling: Detects if game is inside an iframe."""
        try:
            # Check for common iframe selectors
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
        if not user or not pw:
            print("WARNING: Login credentials missing.")
            return

        print("DEBUG: Initiating Login flow...")
        try:
            self.page.wait_for_selector("body", timeout=15000)

            # Handle cookies
            try:
                for t in ["Accept", "Allow", "Agree"]:
                    btn = self.page.locator(f"text={t}").first
                    # is_visible() does not take timeout in Python API
                    if btn.is_visible(): btn.click()
            except: pass

            # Click Login trigger
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

            # Verify Success
            time.sleep(7)
            if self.page.locator("text=Login").first.is_visible():
                raise Exception("Login Verification FAILED.")
            print("DEBUG: LOGIN SUCCESSFUL.")
            self.take_screenshot("post_login_success")
        except Exception as e:
            print(f"DEBUG: Login Error: {e}")
            self.take_screenshot("login_failure")
            raise e

    def navigate_to_spin_game(self):
        """V4.4 Intelligent Game Entry: Employs multi-strategy discovery."""
        try:
            print(f"DEBUG: Navigating to {self.login_url}...")
            self.page.goto(self.login_url, wait_until="networkidle", timeout=60000)
            self.login()

            # STEP 1: Dashboard Validation
            print("DEBUG: Validating dashboard state...")
            try:
                self.page.wait_for_selector("text=Home", timeout=15000)
            except:
                print("WARNING: 'Home' text not found, continuing with discovery...")
            self.take_screenshot("dashboard_state")

            # STEP 2: Intelligent Discovery Hierarchy
            game_found = False

            # Method A: Search-based (Highest precision)
            if self._find_game_via_search():
                game_found = True

            # Method B: Carousel scan (Fallback)
            if not game_found and self._find_game_via_carousel():
                game_found = True

            # Method C: Deep DOM Scan (Final Fallback)
            if not game_found and self._find_game_via_dom_scan():
                game_found = True

            if not game_found:
                print("CRITICAL: Game Discovery Engine failed all strategies.")
                self.take_screenshot("navigation_failure")
                self.dump_dom("navigation_failure_dom")
                raise Exception("INTELLIGENT DISCOVERY FAILED: Game not found.")

            # STEP 3: Game Load Validation (canvas, iframe, or buttons)
            print("DEBUG: Validating game environment...")
            validation_selectors = ["canvas", "iframe", "button:has-text('UP')", "button:has-text('DOWN')"]
            loaded = False
            for sel in validation_selectors:
                try:
                    if self.page.wait_for_selector(sel, timeout=15000):
                        print(f"DEBUG: Game environment VALIDATED via: {sel}")
                        loaded = True
                        break
                except: continue

            if not loaded:
                print("WARNING: Game environment could not be strictly validated.")

            self.take_screenshot("game_entry_final")
            time.sleep(5)
        except Exception as e:
            print(f"CRITICAL: Navigation cycle interrupted: {e}")
            raise e

    def extract_from_network(self) -> List[str]:
        """Multi-Source Intelligence: XHR + WebSocket."""
        outcomes = []

        # Priority 1: Check WebSocket messages
        for msg in reversed(self.ws_messages):
            try:
                data = msg["data"]
                val = data.get("result") or data.get("outcome")
                if val: outcomes.append(str(val).upper()[0])
                if outcomes:
                    print("DEBUG: Intelligence derived from WebSocket.")
                    break
            except: continue

        if outcomes: return outcomes

        # Priority 2: Check XHR/Fetch responses
        for packet in reversed(self.network_responses):
            data = packet["data"]
            try:
                if isinstance(data, dict):
                    val = data.get("result") or data.get("outcome")
                    if val: outcomes.append(str(val).upper()[0])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, str) and item.upper() in ["U", "D"]:
                            outcomes.append(item.upper()[0])
                if outcomes:
                    print("DEBUG: Intelligence derived from Network XHR.")
                    break
            except: continue

        return outcomes

    def detect_repeating_patterns(self) -> List[str]:
        """V4.3 Hardened DOM Scraper (Inside Game/Iframe)."""
        ctx = self.get_active_context()
        print("DEBUG: Hardened Scraper: Scanning active context...")

        # Expanded selectors for V4.3
        game_selectors = [
            "div[class*='history']",
            "div[class*='result']",
            "span:has-text('UP')",
            "span:has-text('DOWN')",
            "xpath=//div[contains(@class,'item')][1]"
        ]

        for sel in game_selectors:
            try:
                elements = ctx.locator(sel).all()
                if elements:
                    outcomes = []
                    for el in elements:
                        text = el.inner_text().strip().upper()
                        if "UP" in text or "U" in text: outcomes.append("U")
                        elif "DOWN" in text or "D" in text: outcomes.append("D")
                    if outcomes:
                        print(f"DEBUG: Scraper SUCCESS via: {sel}")
                        return outcomes
            except: continue

        return []

    def detect_betting_elements(self) -> Dict[str, Optional[ElementHandle]]:
        """Identify interaction points in the active context (Iframe aware)."""
        ctx = self.get_active_context()
        res = {"up": None, "down": None, "amount": None}

        # Use locator().first for better robustness in V4.3
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

    def dump_dom(self, name: str):
        """Dumps the full DOM snapshot for debugging navigation failures."""
        try:
            os.makedirs("artifacts", exist_ok=True)
            content = self.page.content()
            with open(f"artifacts/{name}.html", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"DEBUG: DOM snapshot dumped: artifacts/{name}.html")
        except: pass

    def _find_game_via_search(self) -> bool:
        """Strategy 1: Search-based navigation."""
        print("DEBUG: Searching for game via search bar...")
        try:
            # Locate search input
            search_input = self.page.locator("input[placeholder*='Search'], input[type='search']").first
            search_input.wait_for(state="visible", timeout=5000)
            if search_input.is_visible():
                search_input.click()
                search_input.fill("spin")
                time.sleep(2)

                # Click first matching result
                result = self.page.locator("text=Spin").or_(self.page.locator("[class*='spin']")).first
                result.wait_for(state="visible", timeout=5000)
                if result.is_visible():
                    result.click()
                    print("DEBUG: Game found via Search.")
                    return True
        except: pass
        return False

    def _find_game_via_carousel(self) -> bool:
        """Strategy 2: Carousel/Slider scanning."""
        print("DEBUG: Searching for game via carousel...")
        try:
            carousel = self.page.locator("div[class*='carousel'], div[class*='slider']").first
            carousel.wait_for(state="visible", timeout=5000)
            if carousel.is_visible():
                # Scroll horizontally to trigger lazy loading
                self.page.mouse.wheel(1000, 0)
                time.sleep(2)

                # Extract all visible game cards
                cards = self.page.locator("div[class*='game'], div[class*='card']").all()
                for card in cards:
                    text = card.inner_text()
                    if any(x in text for x in ["Spin", "Bottle", "Da Bottle"]):
                        card.click()
                        print("DEBUG: Game found via Carousel.")
                        return True
        except: pass
        return False

    def _find_game_via_dom_scan(self) -> bool:
        """Strategy 3: Global DOM text scan."""
        print("DEBUG: Searching for game via global DOM scan...")
        try:
            elements = self.page.locator("a, div, span").all()
            for el in elements:
                if not el.is_visible(): continue
                text = el.inner_text()
                if any(x in text for x in ["Spin", "Bottle", "Da Bottle"]):
                    # Click first visible clickable parent/element
                    el.click()
                    print("DEBUG: Game found via DOM scan.")
                    return True
        except: pass
        return False

    def close(self):
        try:
            self.browser.close()
            self.playwright.stop()
        except: pass
