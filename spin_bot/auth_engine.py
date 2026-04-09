import os
import asyncio
import json
import time
import random
from playwright.async_api import async_playwright, BrowserContext, Page
from spin_bot.database import TitanDatabase
from spin_bot.interaction import TitanInteractionSuite
from typing import Optional, Dict, Any

class TitanAuthEngine:
    def __init__(self, db: TitanDatabase):
        self.db = db
        self.phone = os.getenv("FOOTBALL_NG_LOGIN")
        self.password = os.getenv("FOOTBALL_NG_PASS")

    async def ensure_session(self) -> bool:
        """Master Gate: Probes Session state, repairs via Judo UI strategy if needed."""
        state = self.db.load_storage_state()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            # PHASE 1: MAXIMUM STEALTH CONTEXT
            context = await browser.new_context(
                storage_state=state,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
                viewport={'width': 390, 'height': 844},
                device_scale_factor=3,
                is_mobile=True,
                has_touch=True,
                ignore_https_errors=True,
                extra_http_headers={"x-platform": "WAP"}
            )

            # PHASE 2: ANTI-WEBDRIVER INJECTION
            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

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

            print("WARNING: Session invalid. Engaging Judo UI Re-Auth...")

            # Step 2: Judo UI Login Sequence
            success = await self._judo_ui_login(page, context)
            if success:
                state = await context.storage_state()
                self.db.save_storage_state(state)
                await browser.close()
                return True

            await browser.close()
            return False

    async def _judo_ui_login(self, page: Page, context: BrowserContext) -> bool:
        """PHASE 3: THE JUDO LOGIN SEQUENCE (Router-Aware + Universal Trigger)."""
        try:
            # 1. Navigate to base URL and let Vue router settle
            print("DEBUG: Navigating to base mobile URL...")
            await page.goto("https://www.football.com/ng/m/", wait_until="domcontentloaded")
            await asyncio.sleep(4) # Let the redirect to /livescore or /home finish
            print(f"DEBUG: Router settled on URL -> {page.url}")

            # 2. CSS-Nuke to disable blocking overlays invisibly
            await page.add_style_tag(content="""
                .m-modal, .modal, .overlay, .modal-backdrop, [class*='backdrop'] {
                    display: none !important; pointer-events: none !important; z-index: -1 !important;
                }
            """)

            # 3. Universal Trigger: Find the Profile Icon or Login Button
            print("DEBUG: Executing Universal Login Trigger...")
            login_trigger = page.locator(".icon-profile:visible, .m-icon-profile:visible, button:has-text('Log In'):visible, button:has-text('Login'):visible, .header-login:visible").first

            if await login_trigger.is_visible():
                print("DEBUG: Clicking Login Trigger...")
                await login_trigger.click(force=True)
                await asyncio.sleep(2) # Wait for login modal animation
            else:
                print("WARNING: Universal trigger not found. Forcing JS modal trigger...")
                # Fallback: Many Vue apps expose the login path via JS router
                await page.evaluate("window.location.href = '/ng/m/login'")
                await asyncio.sleep(4)
                await page.wait_for_load_state("networkidle")

            # 4. Fill Credentials dynamically
            print("DEBUG: Filling login credentials...")
            phone_input = page.locator("input[type='tel']:visible, input[name='phone']:visible, .m-input-phone input:visible").first
            await phone_input.wait_for(state="visible", timeout=15000)

            # Human-like typing
            await phone_input.click()
            await phone_input.fill("")
            await phone_input.type(self.phone, delay=random.uniform(50, 150))

            pass_input = page.locator("input[type='password']:visible, .m-input-password input:visible").first
            await pass_input.click()
            await pass_input.type(self.password, delay=random.uniform(50, 150))

            # 5. Submit and Wait
            print("DEBUG: Submitting Login...")
            submit_btn = page.locator("button:has-text('Log In'):visible, button:has-text('Login'):visible, .m-login-btn:visible, button[type='submit']:visible").last
            await submit_btn.click(force=True)

            # Wait for server authentication response and navigation
            try:
                await page.wait_for_selector(".icon-profile, .m-balance, :has-text('Logout')", timeout=15000)
                print("DEBUG: Post-Login Success Indicator Found.")
            except:
                print("DEBUG: No immediate success indicator, waiting for settle...")
                await asyncio.sleep(10)

            # 6. Verify success via state change
            content = await page.content()
            if any(x in content.lower() for x in ["logout", "deposit", "account", "balance", "profile"]):
                print("DEBUG: Judo Login SUCCESS.")
                return True
            else:
                os.makedirs("artifacts", exist_ok=True)
                await page.screenshot(path="artifacts/judo_auth_fail.png")
                print("CRITICAL: Judo Login FAILED.")

        except Exception as e:
            print(f"ERROR: Judo Login crashed: {e}")
        return False
