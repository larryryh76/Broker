import os
import random
import time
import json
from playwright.sync_api import sync_playwright, Page, ElementHandle, Response
from typing import List, Optional, Dict

class PlaywrightClient:
    def __init__(self, login_url: str):
        self.login_url = login_url
        self.playwright = sync_playwright().start()

        # V4.1 Network Buffer
        self.network_responses = []

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
        self.page.on("response", self._handle_response)
        self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Selectors (Configurable via Environment)
        self.SEL_LOGIN_BTN = os.getenv("SELECTOR_LOGIN_BTN", "text=Login, button:has-text('Login')")
        self.SEL_USER_INPUT = os.getenv("SELECTOR_USER_INPUT", "input[type='text'], input[type='tel'], input[placeholder*='Mobile']")
        self.SEL_PASS_INPUT = os.getenv("SELECTOR_PASS_INPUT", "input[type='password']")
        self.SEL_SUBMIT_BTN = os.getenv("SELECTOR_SUBMIT_BTN", "button[type='submit'], button:has-text('Sign in'), .login-button")
        self.SEL_VERIFY_SUCCESS = os.getenv("SELECTOR_VERIFY_SUCCESS", ".user-balance, .profile-icon")

    def _handle_response(self, response: Response):
        try:
            url = response.url.lower()
            if any(x in url for x in ["spin", "result", "game", "round", "history"]):
                try:
                    body = response.json()
                    self.network_responses.append({"url": url, "data": body, "timestamp": time.time()})
                except: pass
        except: pass

    def _handle_cookies(self):
        """Attempts to clear cookie popups if present."""
        try:
            cookie_btn = self.page.query_selector("text='Accept', text='Allow cookies', text='I Agree'")
            if cookie_btn and cookie_btn.is_visible():
                cookie_btn.click()
                print("DEBUG: Cookie popup dismissed.")
        except: pass

    def _verify_login_success(self) -> bool:
        """Returns True if the session is authenticated."""
        try:
            # Method 1: Check for success indicator (balance, profile)
            if self.page.locator(self.SEL_VERIFY_SUCCESS).first.is_visible():
                return True

            # Method 2: Check if Login button is GONE
            # We assume if the login trigger is no longer visible, we are in.
            login_trigger = self.page.locator(self.SEL_LOGIN_BTN).first
            if not login_trigger.is_visible():
                return True

            return False
        except:
            return False

    def login(self):
        """Robust Automated Login Logic with retries and verification."""
        user = os.getenv("FOOTBALL_NG_LOGIN")
        pw = os.getenv("FOOTBALL_NG_PASS")
        if not user or not pw:
            print("WARNING: Login credentials missing in environment.")
            return

        max_retries = 3
        for attempt in range(1, max_retries + 1):
            print(f"DEBUG: Login Attempt {attempt}/{max_retries} for {user}...")
            try:
                self.take_screenshot(f"login_attempt_{attempt}_pre")
                self._handle_cookies()

                # 1. Trigger Login Modal/Page
                login_btn = self.page.locator(self.SEL_LOGIN_BTN).first
                if login_btn.is_visible():
                    login_btn.click()
                    time.sleep(random.uniform(1.5, 3.0))

                # 2. Wait for Form
                self.page.wait_for_selector(self.SEL_PASS_INPUT, state="visible", timeout=10000)
                self.take_screenshot(f"login_attempt_{attempt}_form")

                # 3. Fill safely with jitter
                user_input = self.page.locator(self.SEL_USER_INPUT).first
                pass_input = self.page.locator(self.SEL_PASS_INPUT).first

                user_input.click()
                time.sleep(random.uniform(0.5, 1.5))
                user_input.fill(user)

                time.sleep(random.uniform(1.0, 2.0))

                pass_input.click()
                time.sleep(random.uniform(0.5, 1.5))
                pass_input.fill(pw)

                time.sleep(random.uniform(1.5, 3.0))

                # 4. Submit
                submit_btn = self.page.locator(self.SEL_SUBMIT_BTN).first
                submit_btn.click()

                # 5. Wait for transition
                print("DEBUG: Form submitted. Waiting for authentication...")
                time.sleep(7)

                # 6. Verify
                if self._verify_login_success():
                    print("DEBUG: LOGIN SUCCESS confirmed.")
                    self.take_screenshot(f"login_success_attempt_{attempt}")
                    return
                else:
                    print(f"DEBUG: Login verification failed on attempt {attempt}.")
                    self.take_screenshot(f"login_failed_attempt_{attempt}")

            except Exception as e:
                print(f"DEBUG: Login interaction error on attempt {attempt}: {e}")
                self.take_screenshot(f"login_error_attempt_{attempt}")

        # If we reach here, all retries failed
        raise Exception(f"CRITICAL: Failed to login after {max_retries} attempts.")

    def extract_from_network(self) -> List[str]:
        outcomes = []
        for packet in reversed(self.network_responses):
            data = packet["data"]
            try:
                if isinstance(data, dict):
                    val = data.get("result") or data.get("outcome")
                    if val: outcomes.append(str(val).upper()[0])
                elif isinstance(data, list):
                    for item in data:
                        if isinstance(item, str) and item.upper() in ["U", "D", "UP", "DOWN"]:
                            outcomes.append(item.upper()[0])
                if outcomes: break
            except: continue
        return outcomes

    def _is_element_valid(self, el: ElementHandle) -> bool:
        try: return el.evaluate("el => el instanceof HTMLElement && el.offsetParent !== null")
        except: return False

    def detect_repeating_patterns(self) -> List[str]:
        elements = self.page.query_selector_all("div, span, section")
        best = []
        for el in elements:
            if not self._is_element_valid(el): continue
            children = el.query_selector_all(":scope > *")
            if len(children) < 5: continue
            potential = []
            for c in children:
                t = c.inner_text().strip().upper()
                if t in ["U", "D", "UP", "DOWN"] or len(t) == 1: potential.append(t[0])
            if len(potential) > len(best): best = potential
        return best

    def detect_betting_elements(self) -> Dict[str, Optional[ElementHandle]]:
        """V4.1 Self-Discovery: Identify buttons and inputs via heuristics."""
        res = {"up": None, "down": None, "amount": None}
        btns = self.page.query_selector_all("button, [role='button'], .btn")
        for b in btns:
            if not self._is_element_valid(b): continue
            t = b.inner_text().strip().upper()
            c = b.evaluate("el => getComputedStyle(el).backgroundColor")
            if any(x in t for x in ["UP", "BUY", "RISE"]) or "rgb(0," in c: res["up"] = b
            elif any(x in t for x in ["DOWN", "SELL", "FALL"]) or "rgb(255, 0" in c: res["down"] = b

        inputs = self.page.query_selector_all("input")
        for i in inputs:
            if self._is_element_valid(i):
                res["amount"] = i
                break
        return res

    def take_screenshot(self, name: str):
        try:
            os.makedirs("artifacts", exist_ok=True)
            self.page.screenshot(path=f"artifacts/{name}_{int(time.time())}.png")
        except: pass

    def navigate_to_spin_game(self):
        try:
            print(f"DEBUG: Navigating to {self.login_url}...")
            self.page.goto(self.login_url, wait_until="networkidle", timeout=60000)
            self.take_screenshot("navigation_start")
            self.login()
            time.sleep(5)
        except Exception as e:
            print(f"CRITICAL: Navigation/Login failed: {e}")
            raise e

    def close(self):
        try:
            self.browser.close()
            self.playwright.stop()
        except: pass
