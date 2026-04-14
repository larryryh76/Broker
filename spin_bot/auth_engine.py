import os
import asyncio
import json
import time
import random
from playwright.async_api import async_playwright, BrowserContext, Page, Route
from spin_bot.database import TitanDatabase
from spin_bot.interaction import TitanInteractionSuite
from typing import Optional, Dict, Any

class TitanAuthEngine:
    def __init__(self, db: TitanDatabase):
        self.db = db
        self.phone = os.getenv("FOOTBALL_NG_LOGIN")
        self.password = os.getenv("FOOTBALL_NG_PASS")

    async def ensure_session(self) -> bool:
        """Master Gate: Probes Session state, repairs via Ghost Protocol if needed."""
        state = self.db.load_storage_state()

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)

            # V5.58: iPhone 13 Emulation for maximum stability
            iphone_13 = p.devices['iPhone 13']
            context = await browser.new_context(
                **iphone_13,
                storage_state=state,
                ignore_https_errors=True,
                extra_http_headers={"x-platform": "WAP"}
            )

            page = await context.new_page()
            await page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            # Step 1: Fast Probe
            try:
                print("DEBUG: Probing session validity...")
                await page.goto("https://www.football.com/ng/m/home", wait_until="domcontentloaded", timeout=15000)
                await TitanInteractionSuite.stabilize_environment(page)

                indicators = [".icon-profile", ".m-balance", ":has-text('Deposit')", ":has-text('Logout')"]
                for ind in indicators:
                    if await page.locator(ind).count() > 0:
                        print("DEBUG: Immortal Session still valid.")
                        await browser.close()
                        return True
            except: pass

            print("WARNING: Session invalid. Engaging Ghost Protocol Re-Auth...")

            # Step 2: Ghost Protocol Login Sequence
            success = await self._ghost_protocol_login(page, context)
            if success:
                state = await context.storage_state()
                self.db.save_storage_state(state)
                await browser.close()
                return True

            await browser.close()
            return False

    async def _ghost_protocol_login(self, page: Page, context: BrowserContext) -> bool:
        """PHASE 3: THE GHOST PROTOCOL (V5.43 Refined)."""
        try:
            # 1. Police Blockade: Block /livescore redirects
            async def intercept_route(route: Route):
                if "livescore" in route.request.url and route.request.is_navigation_request():
                    print(f"DEBUG: Blocked malicious redirect to: {route.request.url}")
                    await route.abort()
                else:
                    await route.continue_()
            await page.route("**/*", intercept_route)

            # 2. Force-load login page
            print("DEBUG: Force-loading Login Page...")
            try:
                await page.goto("https://www.football.com/ng/m/login", wait_until="commit", timeout=30000)
                await page.wait_for_load_state("networkidle", timeout=15000)
                await asyncio.sleep(3)
            except: pass

            # 3. Nuclear Deep-Injected Login (V2)
            print("DEBUG: Executing Deep-Injected Login (V2)...")
            try:
                await page.evaluate(f"""
                    async (creds) => {{
                        const findAndFill = (selector, val) => {{
                            const el = document.querySelector(selector);
                            if (el) {{
                                el.value = val;
                                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                                return true;
                            }}
                            return false;
                        }};
                        findAndFill("input[type='tel'], input[name='phone']", creds.phone);
                        await new Promise(r => setTimeout(r, 600));
                        findAndFill("input[type='password']", creds.pass);
                        await new Promise(r => setTimeout(r, 1000));
                        const buttons = Array.from(document.querySelectorAll('button'));
                        const loginBtn = buttons.find(b =>
                            b.innerText.includes('Login') || b.innerText.includes('Log In') ||
                            b.classList.contains('m-btn-login') || b.classList.contains('btn-primary')
                        );
                        if (loginBtn) loginBtn.click();
                    }}
                """, {"phone": self.phone, "pass": self.password})
            except Exception as e:
                if "Execution context was destroyed" in str(e) or "Target closed" in str(e):
                    print("DEBUG: Execution context destroyed - Login triggered.")
                else: raise e

            # 4. Wait for confirmation
            print("DEBUG: Waiting for auth settle...")
            await asyncio.sleep(10)

            final_cookies = await context.cookies()
            auth_cookie_names = ["token", "sid", "auth", "session"]
            has_auth_cookie = any(c['name'].lower() in auth_cookie_names for c in final_cookies)

            content = await page.content()
            has_indicator = any(x in content.lower() for x in ["logout", "deposit", "account", "balance"])

            if has_auth_cookie or has_indicator:
                print("SUCCESS: Immortal Session captured.")
                return True
        except Exception as e:
            print(f"ERROR: Ghost Protocol failed: {e}")
        return False
