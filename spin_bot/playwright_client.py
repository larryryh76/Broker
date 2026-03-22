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
        """Automated Login Logic for Football.com Nigeria."""
        user = os.getenv("FOOTBALL_NG_LOGIN")
        pw = os.getenv("FOOTBALL_NG_PASS")
        if not user or not pw: return

        print(f"DEBUG: Attempting login for {user}...")
        try:
            # Heuristic Login Detection
            login_btn = self.page.query_selector("text='Login', text='Sign In'")
            if login_btn: login_btn.click()

            time.sleep(2)
            user_input = self.page.query_selector("input[type='text'], input[type='tel'], input[placeholder*='Mobile']")
            pass_input = self.page.query_selector("input[type='password']")

            if user_input and pass_input:
                user_input.fill(user)
                pass_input.fill(pw)
                submit = self.page.query_selector("button[type='submit'], .login-button")
                if submit: submit.click()
                time.sleep(5)
                print("DEBUG: Login form submitted.")
        except Exception as e:
            print(f"DEBUG: Login failed: {e}")

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
            self.page.goto(self.login_url, wait_until="networkidle", timeout=60000)
            self.login()
            time.sleep(5)
        except: pass

    def close(self):
        try:
            self.browser.close()
            self.playwright.stop()
        except: pass
