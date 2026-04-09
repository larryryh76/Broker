import os
import asyncio
import json
import time
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
        """Master Gate: Probes Game Page for Auth state, repairs if needed."""
        state = self.db.load_storage_state()
        game_url = "https://www.football.com/ng/m/games/spin-da-bottle"

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

            # Step 1: Probe Game Page Directly (Bypass Homepage Redirects)
            try:
                print(f"DEBUG: Probing Game Page Auth state -> {game_url}")
                await page.goto(game_url, wait_until="networkidle", timeout=30000)
                await TitanInteractionSuite.stabilize_environment(page)

                # Check for positive indicators
                indicators = [".icon-profile", ".m-balance", ":has-text('Deposit')", ":has-text('Logout')"]
                for ind in indicators:
                    if await page.locator(ind).count() > 0:
                        print("DEBUG: Immortal Session is valid on Game Page.")
                        await browser.close()
                        return True
            except Exception as e:
                print(f"WARNING: Probe failed: {e}")

            print("WARNING: Session invalid. Engaging API-Level Bypass...")

            # Step 2: Attempt API-Level Authentication
            success = await self._api_login(context)
            if success:
                state = await context.storage_state()
                self.db.save_storage_state(state)
                await browser.close()
                return True

            # Step 3: Fallback to Sterilized UI Login on Game Page
            print("DEBUG: API Bypass failed. Engaging Sterilized Game-Page Login...")
            success = await self._sterilized_game_login(page)
            if success:
                state = await context.storage_state()
                self.db.save_storage_state(state)
                await browser.close()
                return True

            await browser.close()
            return False

    async def _api_login(self, context: BrowserContext) -> bool:
        """PHASE 2: API-Level Authentication Bypass."""
        print("DEBUG: Executing API POST Login...")
        try:
            payload = {"username": self.phone, "password": self.password, "platform": "WAP"}
            headers = {"Content-Type": "application/json", "Origin": "https://www.football.com"}

            response = await context.request.post(
                "https://www.football.com/api/ng/auth/login",
                data=payload, headers=headers, timeout=15000
            )

            if response.status == 200:
                print("DEBUG: API Login SUCCESS.")
                return True
            else:
                print(f"DEBUG: API Login rejected ({response.status}).")
        except Exception as e:
            print(f"ERROR: API Auth failed: {e}")
        return False

    async def _sterilized_game_login(self, page) -> bool:
        """PHASE 3: Sterilized UI Login (DOM-NUKE + Omni-Trigger)."""
        game_url = "https://www.football.com/ng/m/games/spin-da-bottle"

        # 1. Block Vue traps
        await page.route("**/*.{png,jpg,jpeg,svg,gif,webp}", lambda r: r.abort())
        await page.route("**/*modal*.js", lambda r: r.abort())
        await page.route("**/*popup*.js", lambda r: r.abort())

        try:
            print(f"DEBUG: Navigating to Sterilized Game Route -> {game_url}")
            await page.goto(game_url, wait_until="networkidle")
            await TitanInteractionSuite.stabilize_environment(page)

            # 2. Omni-Trigger on Game Page
            omni_sel = "button:has-text('Login'), a:has-text('Login'), .header-login, .m-btn-login, .icon-profile"
            trigger = page.locator(omni_sel).filter(has=page.locator(":visible")).first

            if await trigger.count() > 0:
                print("DEBUG: Game-Page Login Trigger found. Clicking...")
                await trigger.click(force=True)
                await asyncio.sleep(2) # Wait for Vue animation

                phone_input = page.locator("input[type='tel'], input[placeholder*='Mobile']").first
                await phone_input.wait_for(state="visible", timeout=10000)
                await phone_input.fill(self.phone)

                pass_input = page.locator("input[type='password']").first
                await pass_input.fill(self.password)

                print("DEBUG: Submitting Sterilized Login...")
                await pass_input.press("Enter")
                await asyncio.sleep(8)

                content = await page.content()
                if any(x in content.lower() for x in ["logout", "deposit", "account"]):
                    print("DEBUG: Sterilized Game Login SUCCESS.")
                    return True
            else:
                print("CRITICAL: No Login trigger found on sterilized Game Page.")
        except Exception as e:
            print(f"ERROR: Sterilized Game login crashed: {e}")
        return False
