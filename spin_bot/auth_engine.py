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

            # PHASE 1: MAXIMUM STEALTH CONTEXT (Ghost Protocol)
            context = await browser.new_context(
                storage_state=state,
                user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
                viewport={'width': 390, 'height': 844},
                device_scale_factor=3,
                is_mobile=True,
                has_touch=True,
                locale="en-GB",
                timezone_id="Africa/Lagos",
                permissions=["geolocation"],
                color_scheme="dark",
                ignore_https_errors=True,
                extra_http_headers={"x-platform": "WAP"}
            )

            # PHASE 2: DEEP STEALTH HARDWARE SPOOFING
            page = await context.new_page()
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                Object.defineProperty(navigator, 'platform', {get: () => 'iPhone'});
            """)

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

            print("WARNING: Session invalid. Engaging Ghost Protocol Re-Auth...")

            # Step 2: Ghost Protocol UI Login Sequence
            success = await self._ghost_protocol_login(page, context)
            if success:
                state = await context.storage_state()
                self.db.save_storage_state(state)
                await browser.close()
                return True

            await browser.close()
            return False

    async def _ghost_protocol_login(self, page: Page, context: BrowserContext) -> bool:
        """PHASE 3: THE GHOST PROTOCOL (Surgical Interception + Nuclear Injection)."""
        try:
            # 1. Surgical Route Interception: Only block main-frame navigation hijacks
            async def intercept_route(route: Route):
                if "livescore" in route.request.url and route.request.is_navigation_request():
                    print(f"DEBUG: Blocked Navigation Hijack to: {route.request.url}")
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

            # 4. Nuclear JS-Injected Login (Deep Injection)
            print("DEBUG: Executing Nuclear Deep-Injected Login...")
            await page.evaluate(f"""
                async (creds) => {{
                    const findAndFill = (selector, val) => {{
                        const el = document.querySelector(selector);
                        if (el) {{
                            el.value = val;
                            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                            el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }};

                    findAndFill("input[type='tel'], input[name='phone'], .m-input-phone input", creds.phone);
                    await new Promise(r => setTimeout(r, 500));
                    findAndFill("input[type='password'], .m-input-password input", creds.pass);

                    await new Promise(r => setTimeout(r, 1000));
                    const loginBtn = document.querySelector("button[type='submit'], .m-login-btn, button:has-text('Login'), button:has-text('Log In'), .btn-primary");
                    if (loginBtn) {{
                        loginBtn.click();
                    }} else {{
                         // Fallback: Dispatch Enter on password field
                         const passInput = document.querySelector("input[type='password'], .m-input-password input");
                         if (passInput) {{
                             passInput.dispatchEvent(new KeyboardEvent('keydown', {{
                                key: 'Enter', code: 'Enter', which: 13, keyCode: 13, bubbles: true
                             }}));
                         }}
                    }}
                }}
            """, {"phone": self.phone, "pass": self.password})

            # 5. Wait for Authentication Confirmation
            print("DEBUG: Waiting for Ghost Protocol authentication...")
            await asyncio.sleep(10)

            final_cookies = await context.cookies()
            auth_cookie_names = ["token", "sid", "auth", "session", "user_id"]
            has_auth_cookie = any(c['name'].lower() in auth_cookie_names for c in final_cookies)

            content = await page.content()
            has_indicator = any(x in content.lower() for x in ["logout", "deposit", "account", "balance", "profile"])

            if has_auth_cookie or has_indicator:
                print(f"SUCCESS: Ghost Protocol captured immortal session. (Cookie: {has_auth_cookie}, Indicator: {has_indicator})")
                return True
            else:
                os.makedirs("artifacts", exist_ok=True)
                await page.screenshot(path="artifacts/ghost_auth_fail.png")
                print("CRITICAL: Ghost Protocol Login FAILED.")

        except Exception as e:
            print(f"ERROR: Ghost Protocol Login crashed: {e}")
        return False
