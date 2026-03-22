import os
import random
import time
from playwright.sync_api import sync_playwright, Page, ElementHandle
from typing import List, Optional, Dict

class PlaywrightClient:
    def __init__(self, login_url: str):
        self.login_url = login_url
        self.playwright = sync_playwright().start()

        # Hardened Anti-Detection Launch Arguments
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

        # Realistic and Randomized User-Agent Fingerprinting
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/115.0"
        ]

        self.context = self.browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={"width": random.randint(1280, 1920), "height": random.randint(720, 1080)},
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False
        )

        self.page = self.context.new_page()

        # Native Webdriver Spoof (Replacing Stealth Library)
        self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

        # Selectors (Defaults/Loaded from DB)
        self.selectors = {
            "history": os.getenv("SELECTOR_HISTORY", ""),
            "amount": os.getenv("SELECTOR_AMOUNT", ""),
            "up": os.getenv("SELECTOR_UP", ""),
            "down": os.getenv("SELECTOR_DOWN", "")
        }

    def _jitter(self, min_sec=0.8, max_sec=2.5):
        time.sleep(random.uniform(min_sec, max_sec))

    def take_screenshot(self, name: str):
        try:
            os.makedirs("artifacts", exist_ok=True)
            path = f"artifacts/{name}_{int(time.time())}.png"
            self.page.screenshot(path=path)
            print(f"DEBUG: Screenshot captured: {path}")
        except Exception as e:
            print(f"DEBUG: Failed to take screenshot: {e}")

    def safe_query(self, selector: str, timeout=5000) -> Optional[ElementHandle]:
        """Validates and executes a query without crashing."""
        if not selector or selector.strip() == "": return None
        try:
            return self.page.wait_for_selector(selector, timeout=timeout)
        except:
            return None

    def scan_all_elements(self) -> List[ElementHandle]:
        """Scans the DOM for visible interactive elements."""
        try:
            return self.page.query_selector_all("button, input, a, div[role='button'], span")
        except:
            return []

    def detect_repeating_patterns(self) -> List[str]:
        """Self-healing scraper to extract spin history from unknown DOM."""
        print("DEBUG: Self-Healing: Scanning DOM for repeating patterns...")

        # Strategy: Look for containers with many similar children containing U/D or colored balls
        elements = self.page.query_selector_all("div, section, ul")
        best_candidate = []

        for el in elements:
            children = el.query_selector_all(":scope > *")
            if len(children) < 5: continue

            # Check children for "U", "D", or color properties
            potential_history = []
            for child in children:
                text = child.inner_text().strip().upper()
                if text in ["U", "D", "UP", "DOWN", "W", "L"] or len(text) == 1:
                    potential_history.append(text[0] if text else "?")

            if len(potential_history) >= 5:
                if len(potential_history) > len(best_candidate):
                    best_candidate = potential_history

        if best_candidate:
            print(f"DEBUG: Self-Healing SUCCESS: Found pattern: {''.join(best_candidate)}")
            return [x if x in ["U", "D"] else random.choice(["U", "D"]) for x in best_candidate]

        return []

    def detect_betting_elements(self) -> Dict[str, Optional[ElementHandle]]:
        """Automatically identify buttons and inputs via heuristics."""
        print("DEBUG: Self-Healing: Detecting betting UI elements...")
        results = {"up": None, "down": None, "amount": None}

        # 1. Detect Buttons
        btns = self.page.query_selector_all("button, [role='button'], .btn")
        for b in btns:
            text = b.inner_text().strip().upper()
            color = b.evaluate("el => getComputedStyle(el).backgroundColor")

            if any(x in text for x in ["UP", "BUY", "RISE"]) or "rgb(0," in color: # Green-ish
                results["up"] = b
            elif any(x in text for x in ["DOWN", "SELL", "FALL"]) or "rgb(255, 0" in color: # Red-ish
                results["down"] = b

        # 2. Detect Input (Nearest to buttons)
        inputs = self.page.query_selector_all("input[type='number'], input")
        if inputs:
            results["amount"] = inputs[0] # Simplest heuristic for betting input

        return results

    def navigate_to_spin_game(self):
        try:
            self.page.goto(self.login_url, wait_until="networkidle", timeout=60000)
            self._jitter(3, 7)
            self.take_screenshot("page_load")
        except Exception as e:
            print(f"CRITICAL: Navigation failed: {e}")
            self.take_screenshot("navigation_error")

    def close(self):
        try:
            self.browser.close()
            self.playwright.stop()
        except:
            pass
