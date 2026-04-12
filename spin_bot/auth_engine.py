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

            # PHASE 1: CHIMERA STEALTH CONTEXT (V5.49)
            # Mixed Fingerprint: Desktop User Agent with Mobile Viewport
            context = await browser.new_context(
                storage_state=state,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
                viewport={'width': 375, 'height': 812},
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

            # PHASE 2: DEEP STEALTH HARDWARE SPOOFING (8 CPUs/8GB RAM)
            page = await context.new_page()
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'deviceMemory', {get: () => 8});
                Object.defineProperty(navigator, 'hardwareConcurrency', {get: () => 8});
                Object.defineProperty(navigator, 'platform', {get: () => 'Win32'});
            """)

            # Step 1: Fast Probe (Mobile Home)
            try:
                print("DEBUG: Probing session validity...")
                # V5.49: Handshake wait before first navigation
                await asyncio.sleep(3)
                await page.goto("https://www.football.com/ng/m/home", wait_until="domcontentloaded", timeout=15000)
                await TitanInteractionSuite.stabilize_environment(page, delay_nuke=True)

                # Check for positive indicators
                indicators = [".icon-profile", ".m-balance", ":has-text('Deposit')", ":has-text('Logout')"]
                for ind in indicators:
                    if await page.locator(ind).count() > 0:
                        print("DEBUG: Immortal Session still valid.")
                        await browser.close()
                        return True
            except: pass

            print("WARNING: Session invalid. Engaging Ghost Protocol (Chimera) Re-Auth...")

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
        """PHASE 3: THE GHOST PROTOCOL (V5.49 Refined)."""
        try:
            # 1. Surgical Route Interception
            async def intercept_route(route: Route):
                if "livescore" in route.request.url and route.request.is_navigation_request():
                    print(f"DEBUG: Blocked Navigation Hijack to: {route.request.url}")
                    await route.abort()
                else:
                    await route.continue_()

            await page.route("**/*", intercept_route)

            # 2. Force-load the login page
            print("DEBUG: Force-loading Login Page (V5.49 Handshake)...")
            await asyncio.sleep(random.uniform(2, 5))
            try:
                await page.goto("https://www.football.com/ng/m/login", wait_until="commit", timeout=30000)
                # Wait for Vue hydration + Cloudflare Handshake
                print("DEBUG: Waiting for Vue/Security handshake...")
                await asyncio.sleep(5)
                await page.wait_for_load_state("networkidle", timeout=15000)
            except Exception as e:
                print(f"DEBUG: Navigation interrupted or slow ({e}), proceeding to injection...")

            # 3. CSS-Nuke with Grace Period
            await TitanInteractionSuite.stabilize_environment(page, delay_nuke=True)

            # 4. Nuclear JS-Injected Login (Deep Injection V2)
            print("DEBUG: Executing Nuclear Deep-Injected Login (V2)...")
            try:
                # Human delay before injection
                await asyncio.sleep(random.uniform(2, 4))
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

                        findAndFill("input[type='tel'], input[name='phone'], .m-input-phone input", creds.phone);
                        await new Promise(r => setTimeout(r, 800));
                        findAndFill("input[type='password'], .m-input-password input", creds.pass);

                        await new Promise(r => setTimeout(r, 1200));

                        const buttons = Array.from(document.querySelectorAll('button'));
                        const loginBtn = buttons.find(b =>
                            b.innerText.includes('Login') ||
                            b.innerText.includes('Log In') ||
                            b.classList.contains('m-btn-login') ||
                            b.classList.contains('btn-primary') ||
                            b.type === 'submit'
                        );

                        if (loginBtn) {{
                            console.log("DEBUG: Login button located, clicking...");
                            loginBtn.click();
                        }} else {{
                            const passInput = document.querySelector("input[type='password'], .m-input-password input");
                            if (passInput) {{
                                passInput.dispatchEvent(new KeyboardEvent('keydown', {{
                                    key: 'Enter', code: 'Enter', which: 13, keyCode: 13, bubbles: true
                                }}));
                            }}
                        }}
                    }}
                """, {"phone": self.phone, "pass": self.password})
            except Exception as e:
                if "Execution context was destroyed" in str(e) or "Target closed" in str(e):
                    print("DEBUG: Execution context destroyed - Login navigation triggered successfully!")
                else:
                    print(f"DEBUG: Unexpected evaluate error: {e}")
                    raise e

            # 5. Wait for Authentication Confirmation
            print("DEBUG: Waiting for redirect to settle...")
            await asyncio.sleep(random.uniform(5, 8))

            final_cookies = await context.cookies()
            auth_cookie_names = ["token", "sid", "auth", "session", "user_id"]
            has_auth_cookie = any(c['name'].lower() in auth_cookie_names for c in final_cookies)

            content = await page.content()
            has_indicator = any(x in content.lower() for x in ["logout", "deposit", "account", "balance", "profile"])

            if has_auth_cookie or has_indicator:
                print(f"SUCCESS: Captured immortal session. (Cookie: {has_auth_cookie}, Indicator: {has_indicator})")
                return True
            else:
                os.makedirs("artifacts", exist_ok=True)
                await page.screenshot(path="artifacts/ghost_auth_fail.png")
                with open("artifacts/ghost_auth_fail.html", "w") as f:
                    f.write(content)
                print("CRITICAL: Re-Auth FAILED. Artifacts saved.")

        except Exception as e:
            print(f"ERROR: Auth process crashed: {e}")
            try:
                os.makedirs("artifacts", exist_ok=True)
                await page.screenshot(path="artifacts/ghost_auth_crash.png")
                with open("artifacts/ghost_auth_crash.html", "w") as f:
                    f.write(await page.content())
            except: pass
        return False
