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
        """Master Gate: Probes Session state, repairs via Police Blockade strategy if needed."""
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

            print("WARNING: Session invalid. Engaging Police Blockade Re-Auth...")

            # Step 2: Police Blockade UI Login Sequence
            success = await self._blockade_ui_login(page, context)
            if success:
                state = await context.storage_state()
                self.db.save_storage_state(state)
                await browser.close()
                return True

            await browser.close()
            return False

    async def _blockade_ui_login(self, page: Page, context: BrowserContext) -> bool:
        """PHASE 3: THE POLICE BLOCKADE (Route Lockdown + JS Injection)."""
        try:
            # 1. Block the redirect trap (livescore redirect)
            async def intercept_route(route: Route):
                if "livescore" in route.request.url:
                    print(f"DEBUG: Blocked malicious redirect to: {route.request.url}")
                    await route.abort()
                else:
                    await route.continue_()

            await page.route("**/*", intercept_route)

            # 2. Force-load the login page
            print("DEBUG: Force-loading Login Page...")
            try:
                await page.goto("https://www.football.com/ng/m/login", wait_until="commit", timeout=30000)
            except Exception as e:
                print(f"DEBUG: Navigation interrupted or slow ({e}), proceeding to injection...")

            # 3. CSS-Nuke to clear the path
            await page.add_style_tag(content="""
                .m-modal, .modal, .overlay, .modal-backdrop, [class*='backdrop'] {
                    display: none !important; pointer-events: none !important; z-index: -1 !important;
                }
            """)

            # 4. The "Last Resort" JavaScript Login
            print("DEBUG: Executing JS-Injected Login...")
            await page.evaluate(f"""
                (creds) => {{
                    const phoneInput = document.querySelector("input[type='tel'], input[name='phone'], .m-input-phone input");
                    const passInput = document.querySelector("input[type='password'], .m-input-password input");

                    if (phoneInput && passInput) {{
                        phoneInput.value = creds.phone;
                        phoneInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        phoneInput.dispatchEvent(new Event('change', {{ bubbles: true }}));

                        passInput.value = creds.pass;
                        passInput.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        passInput.dispatchEvent(new Event('change', {{ bubbles: true }}));

                        setTimeout(() => {{
                            const submitBtn = document.querySelector("button[type='submit'], .m-login-btn, button:has-text('Login'), button:has-text('Log In')");
                            if (submitBtn) submitBtn.click();
                            else {{
                                // Fallback: press Enter on password field
                                const event = new KeyboardEvent('keydown', {{
                                    key: 'Enter', code: 'Enter', which: 13, keyCode: 13, bubbles: true
                                }});
                                passInput.dispatchEvent(event);
                            }}
                        }}, 1000);
                    }}
                }}
            """, {"phone": self.phone, "pass": self.password})

            # 5. Wait for Authentication Confirmation (Cookies or Indicators)
            print("DEBUG: Waiting for auth settle...")
            await asyncio.sleep(10)

            final_cookies = await context.cookies()
            auth_cookie_names = ["token", "sid", "auth", "session", "user_id"]
            has_auth_cookie = any(c['name'].lower() in auth_cookie_names for c in final_cookies)

            content = await page.content()
            has_indicator = any(x in content.lower() for x in ["logout", "deposit", "account", "balance", "profile"])

            if has_auth_cookie or has_indicator:
                print(f"SUCCESS: Immortal Session captured. (Cookie: {has_auth_cookie}, Indicator: {has_indicator})")
                return True
            else:
                os.makedirs("artifacts", exist_ok=True)
                await page.screenshot(path="artifacts/blockade_auth_fail.png")
                print("CRITICAL: Police Blockade Login FAILED.")

        except Exception as e:
            print(f"ERROR: Police Blockade Login crashed: {e}")
        return False
