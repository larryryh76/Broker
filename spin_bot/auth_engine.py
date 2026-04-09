import os
import asyncio
import json
import time
import random
from playwright.async_api import async_playwright, BrowserContext
from spin_bot.database import TitanDatabase
from spin_bot.interaction import TitanInteractionSuite
from typing import Optional, Dict, Any

class TitanAuthEngine:
    def __init__(self, db: TitanDatabase):
        self.db = db
        self.phone = os.getenv("FOOTBALL_NG_LOGIN")
        self.password = os.getenv("FOOTBALL_NG_PASS")

    async def ensure_session(self) -> bool:
        """Master Gate: Probes Session state, repairs via CSS-Sterilized UI if needed."""
        state = self.db.load_storage_state()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                storage_state=state,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
                viewport={'width': 390, 'height': 844},
                extra_http_headers={"x-platform": "WAP"}
            )
            page = await context.new_page()
            await page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")

            # Step 1: Fast Probe (Mobile Home)
            try:
                print("DEBUG: Probing session validity...")
                await page.goto("https://www.football.com/ng/m/home", wait_until="domcontentloaded", timeout=15000)
                await TitanInteractionSuite.stabilize_environment(page)

                # Check for positive indicators
                indicators = [".icon-profile", ".m-balance", ":has-text('Deposit')", ":has-text('Logout')"]
                for ind in indicators:
                    if await page.locator(ind).count() > 0:
                        print("DEBUG: Immortal Session still valid.")
                        await browser.close()
                        return True
            except: pass

            print("WARNING: Session invalid. Engaging CSS-Sterilized UI Re-Auth...")

            # Step 2: Dedicated CSS-Sterilized UI Login
            success = await self._sterilized_ui_login(page)
            if success:
                state = await context.storage_state()
                self.db.save_storage_state(state)
                await browser.close()
                return True

            await browser.close()
            return False

    async def _sterilized_ui_login(self, page) -> bool:
        """PHASE 3: Sterilized UI Login (CSS-Nuke + Dedicated Path)."""
        login_url = "https://www.football.com/ng/m/login"

        # 1. Block HEAVY Assets but LET SCRIPTS RUN (for Vue hydration)
        await page.route("**/*.{png,jpg,jpeg,svg,gif,webp,woff,woff2}", lambda r: r.abort())

        try:
            print(f"DEBUG: Navigating to Standalone Login -> {login_url}")
            await page.goto(login_url, wait_until="networkidle")

            # 2. CSS-NUKE: Hide overlays without breaking reactivity
            await TitanInteractionSuite.stabilize_environment(page)

            # 3. Dedicated Input Interaction
            phone_sel = "input[type='tel']:visible, input[name='phone']:visible, input[placeholder*='Mobile']:visible, .m-input-phone input"
            phone_input = page.locator(phone_sel).first
            await phone_input.wait_for(state="visible", timeout=20000)

            print("DEBUG: Filling Credentials...")
            # Human-like delay
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await phone_input.click()
            await phone_input.fill("") # Clear just in case
            await phone_input.type(self.phone, delay=random.uniform(50, 150))

            pass_input = page.locator("input[type='password']:visible, .m-input-password input").first
            await pass_input.click()
            await pass_input.type(self.password, delay=random.uniform(50, 150))

            submit_sel = "button:has-text('Login'), button:has-text('Log In'), .m-login-btn, button[type='submit']"
            submit_btn = page.locator(submit_sel).filter(visible=True).first

            if await submit_btn.count() > 0:
                print("DEBUG: Submitting Form via Button...")
                await submit_btn.click(force=True)
            else:
                print("DEBUG: Submit button not found, pressing Enter...")
                await pass_input.press("Enter")

            # Wait for navigation or specific success indicator
            try:
                await page.wait_for_selector(".icon-profile, .m-balance, :has-text('Logout')", timeout=15000)
                print("DEBUG: Post-Login Success Indicator Found.")
            except:
                print("DEBUG: No immediate success indicator, waiting for settle...")
                await asyncio.sleep(10)

            # Verify success via state change
            content = await page.content()
            if any(x in content.lower() for x in ["logout", "deposit", "account", "balance", "profile"]):
                print("DEBUG: CSS-Sterilized Login SUCCESS.")
                return True
            else:
                os.makedirs("artifacts", exist_ok=True)
                await page.screenshot(path="artifacts/sterilized_auth_fail.png")
                print("CRITICAL: CSS-Sterilized Login FAILED.")
        except Exception as e:
            print(f"ERROR: Sterilized Game login crashed: {e}")
        return False
