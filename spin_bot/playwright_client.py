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
        """V4.5 Pattern-Based Controlled Navigation."""
        max_page_retries = 2

        for p_attempt in range(max_page_retries + 1):
            try:
                print(f"DEBUG: Navigation Attempt {p_attempt + 1}/{max_page_retries + 1}...")
                self.page.goto(self.login_url, wait_until="networkidle", timeout=60000)
                if p_attempt == 0: self.login()

                # 1. PAGE LOAD HANDLING
                self.page.wait_for_load_state("networkidle")
                time.sleep(random.uniform(2.0, 4.0)) # Human delay

                # 2. TARGET IDENTIFICATION (CONTROLLED SEARCH)
                print("DEBUG: Identifying target game candidates...")
                # Search within likely containers
                candidates = self.page.locator("a, button, div[class*='card'], div[class*='game'], div[class*='item']").all()

                matches = []
                for el in candidates:
                    try:
                        if not el.is_visible(): continue
                        text = el.inner_text().strip()
                        text_lower = text.lower()

                        rank = 0
                        if "spin da bottle" in text_lower: rank = 3
                        elif "spin" in text_lower and "bottle" in text_lower: rank = 2
                        elif "spin" in text_lower: rank = 1

                        if rank > 0:
                            matches.append({"element": el, "text": text, "rank": rank})
                    except: continue

                # Sort by rank descending
                matches.sort(key=lambda x: x["rank"], reverse=True)
                print(f"DEBUG: Found {len(matches)} potential game candidates.")

                for match in matches:
                    el = match["element"]
                    text = match["text"]
                    print(f"DEBUG: Attempting to click match: '{text}' (Rank: {match['rank']})")

                    # 4. SAFE CLICK EXECUTION
                    try:
                        el.scroll_into_view_if_needed()
                        time.sleep(random.uniform(0.5, 1.5))
                        # Click with slight random offset
                        box = el.bounding_box()
                        if box:
                            self.page.mouse.click(
                                box['x'] + box['width']/2 + random.uniform(-5, 5),
                                box['y'] + box['height']/2 + random.uniform(-5, 5)
                            )
                        else:
                            el.click()

                        print("DEBUG: Click executed. Waiting for validation...")
                        time.sleep(5) # Wait for initial transition

                        # 5. GAME LOAD VALIDATION
                        validation_selectors = [
                            "div[class*='history']",
                            "div[class*='result']",
                            "button:has-text('UP')",
                            "button:has-text('DOWN')",
                            "canvas",
                            "iframe"
                        ]

                        ctx = self.get_active_context()
                        for sel in validation_selectors:
                            try:
                                # We check both the main page and the context (iframe aware)
                                if ctx.locator(sel).first.is_visible():
                                    print(f"DEBUG: Game environment VALIDATED via: {sel}")
                                    self.take_screenshot("game_load_success")
                                    return # SUCCESS
                            except: continue

                        print(f"DEBUG: Validation failed for match: '{text}'.")
                    except Exception as e:
                        print(f"DEBUG: Click interaction failed: {e}")

                # 6. FALLBACK: Page refresh if attempt failed
                if p_attempt < max_page_retries:
                    print("DEBUG: Discovery failed on this page state. Refreshing...")
                    self.page.reload()
            except Exception as e:
                print(f"DEBUG: Navigation attempt error: {e}")

        # 7. FAILURE HANDLING
        print("CRITICAL: All discovery and navigation strategies FAILED.")
        self.take_screenshot("navigation_failure")
        self.dump_dom("navigation_failure_dom")
        raise Exception("PATTERN-BASED NAVIGATION FAILED: Could not reach game.")

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

    def close(self):
        try:
            self.browser.close()
            self.playwright.stop()
        except: pass
