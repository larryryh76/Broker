import os
import random
import time
from playwright.sync_api import sync_playwright
try:
    from playwright_stealth import stealth
except ImportError:
    stealth = None
from typing import List, Optional

class PlaywrightClient:
    def __init__(self, login_url: str):
        self.login_url = login_url
        self.playwright = sync_playwright().start()

        # Hardened Launch Arguments for Headless CI/CD
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

        # Realistic User-Agent and Context Configuration
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]

        self.context = self.browser.new_context(
            user_agent=random.choice(user_agents),
            viewport={"width": 1280, "height": 720},
            device_scale_factor=1,
            is_mobile=False,
            has_touch=False
        )

        self.page = self.context.new_page()

        # Apply Stealth if available (Failsafe)
        if stealth:
            try:
                stealth(self.page)
            except Exception as e:
                print(f"Stealth failed: {e}")

        # --- Selector Discovery Engine (Configurable via Environment) ---
        # Game selectors
        self.SEL_HISTORY = os.getenv("SELECTOR_HISTORY", ".history-item")
        self.SEL_AMOUNT = os.getenv("SELECTOR_AMOUNT", "#bet-amount-input")
        self.SEL_UP = os.getenv("SELECTOR_UP", "#bet-up-button")
        self.SEL_DOWN = os.getenv("SELECTOR_DOWN", "#bet-down-button")

        # Login selectors
        self.SEL_LOGIN = os.getenv("SELECTOR_LOGIN", "#login-username")
        self.SEL_PASS = os.getenv("SELECTOR_PASS", "#login-password")
        self.SEL_SUBMIT = os.getenv("SELECTOR_SUBMIT", "#login-submit-btn")

    def _jitter(self, min_sec=0.8, max_sec=2.5):
        time.sleep(random.uniform(min_sec, max_sec))

    def take_screenshot(self, name: str):
        """Captures a screenshot for debugging and selector discovery."""
        try:
            os.makedirs("artifacts", exist_ok=True)
            path = f"artifacts/{name}_{int(time.time())}.png"
            self.page.screenshot(path=path)
            print(f"Screenshot saved: {path}")
        except Exception as e:
            print(f"Failed to take screenshot: {e}")

    def login(self):
        """Perform automated login based on target site UI."""
        username = os.getenv("FOOTBALL_NG_LOGIN")
        password = os.getenv("FOOTBALL_NG_PASS")

        if not username or not password:
            print("Login credentials missing. Skipping login.")
            return

        print(f"Attempting login for user: {username}")
        try:
            self._jitter(2, 4)
            # 1. Fill credentials
            self.page.wait_for_selector(self.SEL_LOGIN, timeout=10000)
            self.page.fill(self.SEL_LOGIN, username)
            self.page.fill(self.SEL_PASS, password)
            self._jitter(0.5, 1.5)
            # 2. Click submit
            self.page.click(self.SEL_SUBMIT)
            self._jitter(3, 6) # Wait for login redirect
            self.take_screenshot("post_login")
        except Exception as e:
            print(f"Login interaction failed: {e}")
            self.take_screenshot("login_error")

    def navigate_to_spin_game(self):
        """Navigate to the target game and authenticate."""
        try:
            print(f"Navigating to {self.login_url}...")
            self.page.goto(self.login_url, wait_until="networkidle", timeout=60000)
            self._jitter(3, 7)

            # Check if login is required (e.g., look for a login button or form)
            if self.page.query_selector(self.SEL_LOGIN):
                self.login()

            self.take_screenshot("game_page_load")
        except Exception as e:
            print(f"Navigation failed: {e}")
            self.take_screenshot("navigation_error")

    def get_latest_outcomes(self) -> List[str]:
        """Scrape the history of spin results from the DOM."""
        try:
            self.page.wait_for_selector(self.SEL_HISTORY, timeout=15000)
            items = self.page.query_selector_all(self.SEL_HISTORY)
            outcomes = []
            for item in items:
                text = item.inner_text().strip().upper()
                if "UP" in text or "U" in text: outcomes.append("U")
                elif "DOWN" in text or "D" in text: outcomes.append("D")
            return outcomes
        except Exception as e:
            print(f"Scraping failed or timed out: {e}")
            self.take_screenshot("scraping_error")
            return []

    def place_bet(self, amount: float, direction: str):
        """Execute the bet via UI interaction with human-like timing."""
        try:
            self._jitter(1.5, 3.5)
            print(f"Executing Bet: ₦{amount} on {direction}")

            # 1. Wait for and interact with the amount input
            self.page.wait_for_selector(self.SEL_AMOUNT, timeout=10000)
            self.page.click(self.SEL_AMOUNT) # Initial click for focus
            self.page.fill(self.SEL_AMOUNT, str(amount))
            self._jitter(0.5, 1.2)

            # 2. Select the direction button
            target = self.SEL_UP if direction == "U" else self.SEL_DOWN
            self.page.hover(target)
            self._jitter(0.2, 0.6)
            self.page.click(target)

            # 3. Success Capture
            self.take_screenshot(f"bet_placed_{direction}")
            self._jitter(10, 15) # Wait for spin completion animation
        except Exception as e:
            print(f"Bet placement failed: {e}")
            self.take_screenshot("bet_error")

    def close(self):
        """Gracefully shutdown the browser."""
        try:
            self.browser.close()
            self.playwright.stop()
        except Exception as e:
            print(f"Browser shutdown failed: {e}")
