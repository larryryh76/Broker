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

    def _handle_response(self, response: Response):
        try:
            url = response.url.lower()
            if any(x in url for x in ["spin", "result", "game", "round", "history"]):
                try:
                    body = response.json()
                    self.network_responses.append({"url": url, "data": body, "timestamp": time.time()})
                except: pass
        except: pass

    def login(self):
        """Robust Modal-Based Login Logic for Football.com Nigeria."""
        user = os.getenv("FOOTBALL_NG_LOGIN")
        pw = os.getenv("FOOTBALL_NG_PASS")
        if not user or not pw:
            print("WARNING: Login credentials missing in environment.")
            return

        max_retries = 2
        for attempt in range(1, max_retries + 2):
            print(f"DEBUG: Login Attempt {attempt}/{max_retries + 1}...")
            try:
                # 1. WAIT FOR PAGE LOAD
                self.page.wait_for_selector("body", timeout=15000)
                self.take_screenshot(f"login_step1_load_{attempt}")

                # 2. HANDLE COOKIE POPUP (VERY IMPORTANT)
                try:
                    for text in ["Accept", "Allow", "Agree", "Got it"]:
                        btn = self.page.locator(f"text={text}").first
                        if btn.is_visible(timeout=1000):
                            btn.click()
                            print(f"DEBUG: Cookie popup '{text}' dismissed.")
                except: pass

                # 3. CLICK LOGIN BUTTON FIRST (Trigger Modal)
                self.take_screenshot(f"login_step2_pre_click_{attempt}")
                try:
                    # Resilient selectors
                    self.page.locator("text=Login").first.click(timeout=5000)
                except:
                    try:
                        self.page.locator("button:has-text('Login')").click(timeout=5000)
                    except:
                        # Fallback for mobile/other variations
                        self.page.locator(".login-button, .login-trigger, [data-testid='login-button']").first.click(timeout=5000)

                print("DEBUG: Login trigger clicked.")
                self.take_screenshot(f"login_step3_post_click_{attempt}")

                # 4. WAIT FOR LOGIN MODAL
                # Ensure input field for password is ready
                self.page.wait_for_selector("input[type='password']", timeout=15000)
                print("DEBUG: Login modal visible.")
                self.take_screenshot(f"login_step4_modal_ready_{attempt}")

                # 5. HUMAN-LIKE DELAY BEFORE TYPING
                time.sleep(random.uniform(1.5, 3.0))

                # 6. FILL FORM SAFELY
                user_field = self.page.locator("input[type='text'], input[type='tel'], input[placeholder*='Mobile'], input[placeholder*='Phone']").first
                user_field.fill(user)
                time.sleep(random.uniform(0.5, 1.2))

                self.page.fill("input[type='password']", pw)
                print("DEBUG: Credentials filled.")
                self.take_screenshot(f"login_step5_form_filled_{attempt}")

                # 7. CLICK SUBMIT
                try:
                    # In modal systems, the last button with 'Login' text is usually the submit button
                    self.page.locator("button:has-text('Login')").last.click(timeout=5000)
                except:
                    # Fallback submits
                    self.page.locator("button:has-text('Sign in'), button[type='submit'], .login-submit").last.click(timeout=5000)

                print("DEBUG: Submit clicked.")
                self.take_screenshot(f"login_step6_after_submit_{attempt}")

                # 8. VERIFY LOGIN SUCCESS (MANDATORY)
                print("DEBUG: Waiting for authentication verification (5-10s)...")
                time.sleep(random.uniform(5.0, 10.0))

                # If Login text is still visible, we likely failed
                is_login_visible = False
                try:
                    is_login_visible = self.page.locator("text=Login").first.is_visible(timeout=3000)
                except: pass

                if is_login_visible:
                    print(f"DEBUG: Login verification FAILED on attempt {attempt}. Login button still visible.")
                    self.take_screenshot(f"login_failed_verification_{attempt}")
                    if attempt > max_retries:
                        raise Exception("LOGIN FAILED: Verification failed after all retries.")
                    continue # Retry loop
                else:
                    print("DEBUG: LOGIN SUCCESS confirmed.")
                    self.take_screenshot(f"login_final_success_{attempt}")
                    return # Exit success

            except Exception as e:
                print(f"DEBUG: Login interaction error on attempt {attempt}: {e}")
                self.take_screenshot(f"login_exception_{attempt}")
                if attempt > max_retries:
                    raise e

        raise Exception("CRITICAL: Failed to login after multiple attempts.")

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
