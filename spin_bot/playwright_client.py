import os
import random
import time
from playwright.sync_api import sync_playwright, Page, ElementHandle
try:
    from playwright_stealth import stealth
except ImportError:
    stealth = None
from typing import List, Optional, Dict

class PlaywrightClient:
    def __init__(self, login_url: str):
        self.login_url = login_url
        self.playwright = sync_playwright().start()

        # Hardened Launch Arguments
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process"
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
        if stealth:
            try: stealth(self.page)
            except: pass

        # Selectors (Defaults/Fallback)
        self.SEL_HISTORY = os.getenv("SELECTOR_HISTORY")
        self.SEL_AMOUNT = os.getenv("SELECTOR_AMOUNT")
        self.SEL_UP = os.getenv("SELECTOR_UP")
        self.SEL_DOWN = os.getenv("SELECTOR_DOWN")

        # Login selectors
        self.SEL_LOGIN = os.getenv("SELECTOR_LOGIN", "#login-username")
        self.SEL_PASS = os.getenv("SELECTOR_PASS", "#login-password")
        self.SEL_SUBMIT = os.getenv("SELECTOR_SUBMIT", "#login-submit-btn")

    def _jitter(self, min_sec=0.8, max_sec=2.5):
        time.sleep(random.uniform(min_sec, max_sec))

    def take_screenshot(self, name: str):
        try:
            os.makedirs("artifacts", exist_ok=True)
            path = f"artifacts/{name}_{int(time.time())}.png"
            self.page.screenshot(path=path)
            print(f"DEBUG: Screenshot saved {path}")
        except: pass

    def log_html_snippet(self, element: ElementHandle, name: str):
        try:
            snippet = element.inner_html()
            os.makedirs("artifacts", exist_ok=True)
            with open(f"artifacts/{name}_{int(time.time())}.html", "w") as f:
                f.write(snippet)
        except: pass

    def detect_buttons(self) -> Dict[str, Optional[ElementHandle]]:
        """Automatically detect UP and DOWN buttons from the DOM."""
        print("DEBUG: Starting Auto-Detection for Bet Buttons...")

        buttons = self.page.query_selector_all("button, [role='button'], .btn, a")
        up_btn = None
        down_btn = None

        for btn in buttons:
            text = btn.inner_text().strip().upper()
            color = btn.evaluate("el => getComputedStyle(el).backgroundColor")

            # UP detection
            if not up_btn:
                if any(x in text for x in ["UP", "BUY", "RISE", "CALL"]) or "GREEN" in color or "rgb(0," in color:
                    up_btn = btn

            # DOWN detection
            if not down_btn:
                if any(x in text for x in ["DOWN", "SELL", "FALL", "PUT"]) or "RED" in color or "rgb(255, 0" in color:
                    down_btn = btn

        if up_btn: print(f"DEBUG: UP button detected ({up_btn.inner_text()}).")
        if down_btn: print(f"DEBUG: DOWN button detected ({down_btn.inner_text()}).")

        return {"UP": up_btn, "DOWN": down_btn}

    def detect_input(self, buttons: Dict[str, Optional[ElementHandle]]) -> Optional[ElementHandle]:
        """Automatically detect bet input field from the DOM."""
        print("DEBUG: Starting Auto-Detection for Bet Input...")

        inputs = self.page.query_selector_all("input[type='number'], input[type='text']")
        if not inputs: return None

        # Find input closest to either UP or DOWN button
        best_input = None
        min_dist = float('inf')

        btn_el = buttons.get("UP") or buttons.get("DOWN")
        if not btn_el: return inputs[0] # Fallback to first input

        btn_box = btn_el.bounding_box()
        if not btn_box: return inputs[0]

        for input_el in inputs:
            box = input_el.bounding_box()
            if not box: continue

            # Simple Euclidean distance between centers
            dist = ((box['x'] - btn_box['x'])**2 + (box['y'] - btn_box['y'])**2)**0.5
            if dist < min_dist:
                min_dist = dist
                best_input = input_el

        if best_input:
            print(f"DEBUG: Bet Input detected (distance: {min_dist}).")

        return best_input

    def detect_history(self) -> List[str]:
        """Automatically detect spin history from the DOM."""
        print("DEBUG: Starting Auto-Detection for Spin History...")

        # Priority 1: User-provided selector
        if self.SEL_HISTORY:
            try:
                items = self.page.query_selector_all(self.SEL_HISTORY)
                if items:
                    outcomes = self._parse_history_elements(items)
                    if outcomes:
                        print(f"DEBUG: Found {len(outcomes)} items via manual selector.")
                        return outcomes
            except: pass

        # Priority 2: Scanning for repeating small elements with U/D or colored indicators
        # We look for containers with multiple similar children
        containers = self.page.query_selector_all("div, span, section")
        best_group = []

        for container in containers:
            children = container.query_selector_all(":scope > *")
            if len(children) < 3: continue

            # Filter children that look like history items
            valid_children = []
            for child in children:
                text = child.inner_text().strip().upper()
                # Check for "U", "D", "UP", "DOWN" or specific colors if possible
                if text in ["U", "D", "UP", "DOWN", "W", "L"] or len(text) <= 2:
                    valid_children.append(child)

            if len(valid_children) >= 3:
                if len(valid_children) > len(best_group):
                    best_group = valid_children

        if best_group:
            print(f"DEBUG: Auto-detected history group with {len(best_group)} elements.")
            return self._parse_history_elements(best_group)

        print("DEBUG: History auto-detection FAILED.")
        return []

    def _parse_history_elements(self, elements: List[ElementHandle]) -> List[str]:
        outcomes = []
        for el in elements:
            text = el.inner_text().strip().upper()
            if "UP" in text or "U" in text: outcomes.append("U")
            elif "DOWN" in text or "D" in text: outcomes.append("D")
            # Color-based fallback (Playwright evaluate)
            else:
                color = el.evaluate("el => getComputedStyle(el).backgroundColor")
                # Detect red/green-ish colors
                if "rgb(0," in color or "green" in color: outcomes.append("U")
                elif "rgb(255, 0" in color or "red" in color: outcomes.append("D")

        # Return last 10 (or all if less)
        return outcomes[-10:] if outcomes else []

    def login(self):
        username = os.getenv("FOOTBALL_NG_LOGIN")
        password = os.getenv("FOOTBALL_NG_PASS")
        if not username or not password:
            print("Login credentials missing. Skipping login.")
            return

        print(f"Attempting login for user: {username}")
        try:
            self._jitter(2, 4)
            self.page.wait_for_selector(self.SEL_LOGIN, timeout=10000)
            self.page.fill(self.SEL_LOGIN, username)
            self.page.fill(self.SEL_PASS, password)
            self._jitter(0.5, 1.5)
            self.page.click(self.SEL_SUBMIT)
            self._jitter(3, 6)
            self.take_screenshot("post_login")
        except Exception as e:
            print(f"Login failed: {e}")
            self.take_screenshot("login_error")

    def navigate_to_spin_game(self):
        try:
            self.page.goto(self.login_url, wait_until="networkidle", timeout=60000)
            self._jitter(3, 7)
            # Check for login fields
            if self.page.query_selector(self.SEL_LOGIN):
                self.login()
            self.take_screenshot("game_load")
        except Exception as e:
            print(f"Navigation failed: {e}")

    def get_latest_outcomes(self) -> List[str]:
        outcomes = self.detect_history()
        if not outcomes:
            print("AUTO-DETECTION FAILED: History not found.")
            self.take_screenshot("detection_fail_history")
        return outcomes

    def place_bet(self, amount: float, direction: str):
        """Execute the bet via UI interaction with auto-detection."""
        # Safety Check: Full scan if elements not cached or missing
        try:
            self._jitter(1.5, 3.5)

            # 1. Detect Elements
            buttons = self.detect_buttons()
            target_btn = buttons.get(direction)
            input_el = self.detect_input(buttons)

            # 2. Safety Check
            if not target_btn or not input_el:
                print("AUTO-DETECTION FAILED: Critical elements missing. Bet aborted.")
                self.take_screenshot("detection_fail_bet")
                return

            print(f"Executing Bet: ₦{amount} on {direction}")

            # 3. Execution
            input_el.click()
            self._jitter(0.2, 0.5)
            input_el.fill(str(amount))
            self._jitter(0.5, 1.2)

            target_btn.hover()
            self._jitter(0.2, 0.6)
            target_btn.click()

            self.take_screenshot(f"bet_{direction}")
            self._jitter(10, 15) # Wait for result
        except Exception as e:
            print(f"Bet placement failed: {e}")
            self.take_screenshot("bet_error")

    def close(self):
        self.browser.close()
        self.playwright.stop()
