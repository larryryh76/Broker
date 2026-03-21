import os
import random
import time
from playwright.sync_api import sync_playwright
from playwright_stealth import stealth_sync
from typing import List, Optional

class PlaywrightClient:
    def __init__(self, login_url: str):
        self.login_url = login_url
        self.playwright = sync_playwright().start()
        self.browser = self.playwright.chromium.launch(headless=True)
        self.context = self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720}
        )
        self.page = self.context.new_page()
        stealth_sync(self.page)

        # Load Selectors from Environment
        self.SEL_HISTORY = os.getenv("SELECTOR_HISTORY", ".history-item")
        self.SEL_AMOUNT = os.getenv("SELECTOR_AMOUNT", "#bet-amount-input")
        self.SEL_UP = os.getenv("SELECTOR_UP", "#bet-up-button")
        self.SEL_DOWN = os.getenv("SELECTOR_DOWN", "#bet-down-button")

    def _jitter(self, min_sec=0.5, max_sec=2.0):
        time.sleep(random.uniform(min_sec, max_sec))

    def take_screenshot(self, name: str):
        os.makedirs("artifacts", exist_ok=True)
        self.page.screenshot(path=f"artifacts/{name}.png")
        print(f"Screenshot saved: artifacts/{name}.png")

    def login(self):
        """Perform login using credentials from environment."""
        username = os.getenv("FOOTBALL_NG_LOGIN")
        password = os.getenv("FOOTBALL_NG_PASS")

        if not username or not password:
            print("Login credentials missing. Skipping automated login.")
            return

        print(f"Attempting login for user: {username}")
        # Add site-specific login flow here
        # Example:
        # self.page.fill("#username", username)
        # self.page.fill("#password", password)
        # self.page.click("#login-btn")
        # self._jitter(2, 5)

    def navigate_to_spin_game(self):
        self.page.goto(self.login_url)
        self._jitter(3, 7)
        self.login()
        self.take_screenshot("initial_load")

    def get_latest_outcomes(self) -> List[str]:
        """Scrape the history of spins from the DOM."""
        try:
            self.page.wait_for_selector(self.SEL_HISTORY, timeout=10000)
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
        """Execute the bet via UI interaction."""
        try:
            self._jitter(1, 3)
            print(f"BETTED: ₦{amount} on {direction}")

            # Example implementation:
            # self.page.wait_for_selector(self.SEL_AMOUNT, timeout=5000)
            # self.page.fill(self.SEL_AMOUNT, str(amount))
            # if direction == "U":
            #     self.page.click(self.SEL_UP)
            # else:
            #     self.page.click(self.SEL_DOWN)

            self.take_screenshot(f"bet_{direction}")
            self._jitter(5, 10) # Wait for spin result
        except Exception as e:
            print(f"Bet placement failed: {e}")
            self.take_screenshot("bet_error")

    def close(self):
        self.browser.close()
        self.playwright.stop()
