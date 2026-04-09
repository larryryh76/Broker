import os
import sys
import asyncio
import json
import time
import random
from playwright.async_api import async_playwright, Page, BrowserContext, Request, Response
try:
    from playwright_stealth import stealth_async as stealth
except ImportError:
    try:
        from playwright_stealth import stealth
    except ImportError:
        stealth = None
from pymongo import MongoClient
from typing import Optional, Dict, Any, List

class TitanStealthClient:
    def __init__(self):
        self.home_url = "https://www.football.com/ng/m/home"
        self.game_url = "https://www.football.com/ng/m/games/spin-da-bottle"
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.phone = os.getenv("FOOTBALL_NG_LOGIN")
        self.password = os.getenv("FOOTBALL_NG_PASS")
        self.db_client = None
        self.db = None
        self.collection = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.execution_log = []

    def _log(self, message: str):
        print(message)
        self.execution_log.append(f"[{time.ctime()}] {message}")

    async def setup_db(self):
        if not self.mongodb_uri:
            self._log("WARNING: MONGODB_URI not set. Session persistence disabled.")
            return
        try:
            if self.db_client is None:
                self.db_client = MongoClient(self.mongodb_uri)
                self.db = self.db_client.get_database("spin_bot")
                self.collection = self.db.get_collection("sessions")
                self._log("DEBUG: MongoDB connection established.")
        except Exception as e:
            self._log(f"ERROR: MongoDB setup failed: {e}")

    def load_storage_state(self) -> Optional[Dict[str, Any]]:
        """Immortal Session: Restore Session State from MongoDB."""
        path = "artifacts/storage_state.json"
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    state = json.load(f)
                self._log("DEBUG: Loaded storage_state from artifacts.")
                return state
            except: pass

        if self.collection is not None:
            try:
                # V4.1 Alignment: Using titan_auth for session immortality
                doc = self.collection.find_one({"id": "titan_auth"})
                if doc and "state" in doc:
                    self._log("DEBUG: Loaded storage_state from MongoDB (titan_auth).")
                    return doc["state"]
            except: pass
        return None

    async def setup_browser(self, storage_state: Optional[Dict[str, Any]] = None):
        if not self.playwright:
            self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(headless=True)

        # V4.1: Standard mobile platform headers for mobile-app emulation
        extra_headers = {
            "x-platform": "WAP",
            "x-app-id": "1:753470331102:web:ae7465077d2fa908d70a4f"
        }

        # V5.30: Enhanced iPhone 15 Fingerprint to slip past Google Captcha
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            viewport={'width': 390, 'height': 844},
            device_scale_factor=3,
            is_mobile=True,
            has_touch=True,
            locale="en-NG",
            timezone_id="Africa/Lagos",
            geolocation={"latitude": 6.5244, "longitude": 3.3792},
            permissions=["geolocation"],
            storage_state=storage_state,
            ignore_https_errors=True,
            extra_http_headers=extra_headers
        )

        # V5.32.1: Pre-emptive cookie injection to bypass location popup
        await self.context.add_cookies([
            {"name": "region", "value": "NG", "domain": ".football.com", "path": "/"},
            {"name": "currency", "value": "NGN", "domain": ".football.com", "path": "/"}
        ])

        self.page = await self.context.new_page()

        # V5.30: Anti-Detection Injection
        await self.page.add_init_script("delete Object.getPrototypeOf(navigator).webdriver")

        # V5.21 Asset Resilience: Preconnect/DNS-Prefetch
        await self.page.add_init_script("""
            (function() {
                const head = document.head || document.getElementsByTagName('head')[0];
                const domains = ['https://www.football.com', 'https://s.football.com/games/'];
                domains.forEach(url => {
                    const pc = document.createElement('link'); pc.rel = 'preconnect'; pc.href = url; head.appendChild(pc);
                    const dp = document.createElement('link'); dp.rel = 'dns-prefetch'; dp.href = url; head.appendChild(dp);
                });
            })();
        """)

        await self._apply_ui_sensitivity()

        if stealth:
            try: await stealth(self.page)
            except: pass

        self.page.set_default_timeout(15000)

    async def _apply_ui_sensitivity(self):
        self._log("DEBUG: Injecting V5.21 UI Sensitivity Suite...")
        await self.page.add_init_script("""
            (function() {
                // 1. Asset Retry Hook
                window.assetRetries = window.assetRetries || {};
                const originalCreateElement = document.createElement;
                document.createElement = function(tagName) {
                    const element = originalCreateElement.call(document, tagName);
                    if (tagName === 'script' || tagName === 'link') {
                        element.onerror = function() {
                            const src = element.src || element.href;
                            if (!src) return;
                            window.assetRetries[src] = (window.assetRetries[src] || 0) + 1;
                            if (window.assetRetries[src] <= 2) {
                                console.log(`Retrying asset: ${src} (Attempt ${window.assetRetries[src]})`);
                                const newEl = document.createElement(tagName);
                                if (tagName === 'script') newEl.src = src; else newEl.href = src;
                                document.head.appendChild(newEl);
                            } else {
                                console.error(`Fatal Error: Asset load failed after 2 retries: ${src}`);
                                showFatalError(`Failed to load critical asset: ${src}`);
                            }
                        };
                    }
                    return element;
                };

                function showFatalError(msg) {
                    const err = document.createElement('div');
                    err.style = "position:fixed;top:0;left:0;width:100%;background:red;color:white;z-index:9999;padding:10px;text-align:center";
                    err.innerText = "Fatal Error: " + msg;
                    document.body.appendChild(err);
                }

                // 2. Global Modal & Auth Listener
                const originalFetch = window.fetch;
                window.fetch = async (...args) => {
                    const response = await originalFetch(...args);
                    if (response.status === 401) {
                        triggerLoginModal();
                    }
                    return response;
                };

                function triggerLoginModal() {
                    if (document.getElementById('omni-auth-modal')) return;
                    const modal = document.createElement('div');
                    modal.id = 'omni-auth-modal';
                    modal.innerHTML = `
                        <div class="modal-backdrop" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:1052;"></div>
                        <div class="modal-content" style="position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);background:white;padding:20px;z-index:1055;border-radius:8px;text-align:center;width:80%;">
                            <h3>Error! Please login to start game.</h3>
                            <button id="auth-primary" style="background:#007bff;color:white;padding:10px 20px;border:none;border-radius:4px;margin:5px;">Login</button>
                            <button id="auth-secondary" style="background:#6c757d;color:white;padding:10px 20px;border:none;border-radius:4px;margin:5px;">Exit</button>
                        </div>
                    `;
                    document.body.appendChild(modal);
                    document.getElementById('auth-primary').onclick = () => window.location.href = '/ng/m/login';
                    document.getElementById('auth-secondary').onclick = () => {
                        modal.remove();
                        window.history.back() || (window.location.href = '/ng/m/home');
                    };
                }

                // 3. Theme & Z-Index Management
                let modalStack = 0;
                const updateTheme = () => {
                    const theme = document.documentElement.getAttribute('data-theme') || 'light';
                    const brand = window.BRAND_NAME || 'football';
                    const loaders = document.querySelectorAll('.app-init-loader-wrap');
                    const spinners = document.querySelectorAll('.spinner-icon');

                    loaders.forEach(loader => {
                        if (theme === 'light') {
                            loader.style.setProperty('background-color', '#f4f4f4', 'important');
                        } else {
                            loader.style.setProperty('background-color', (brand === 'Encore') ? '#100e26' : '#000000', 'important');
                        }
                    });

                    if (theme === 'light') {
                        spinners.forEach(s => s.style.setProperty('background-color', '#e0e1e2', 'important'));
                    }
                };

                const observer = new MutationObserver(() => {
                    updateTheme();
                    const backdrops = document.querySelectorAll('.modal-backdrop:not([data-managed])');
                    backdrops.forEach(b => {
                        b.style.zIndex = (1052 + (modalStack * 10)).toString();
                        b.setAttribute('data-managed', 'true');
                    });
                    const contents = document.querySelectorAll('.modal-content:not([data-managed])');
                    contents.forEach(c => {
                        c.style.zIndex = (1055 + (modalStack * 10)).toString();
                        c.setAttribute('data-managed', 'true');
                        modalStack++;
                    });
                });
                observer.observe(document.documentElement, { childList: true, subtree: true, attributes: true });
            })();
        """)

    async def hard_anchor_navigation(self, target_url: str, max_attempts: int = 3):
        """V5.30: Bypass & Blast Navigation Lock."""
        for attempt in range(max_attempts):
            self._log(f"DEBUG: Anchoring to Spin da Bottle (Attempt {attempt+1})...")
            await self.page.goto(target_url, wait_until="networkidle")
            # V5.30 mechanical wait for Vue router hijacks
            await asyncio.sleep(3)
            if "livescore" in self.page.url:
                self._log("WARNING: Redirect Hijack detected! Forcing return to Spin da Bottle...")
                continue
            else:
                self._log("DEBUG: Navigation anchored successfully.")
                break

    async def stabilize_environment(self, max_attempts: int = 3):
        """V5.34: Non-blocking Overlay Clearance Protocol (DOM-NUKE)."""
        self._log("DEBUG: Checking for Regional Splash & Overlays...")
        # V5.34: Initial settlement wait for Vue/Nuxt hydration
        await asyncio.sleep(2)

        # 1. DOM-NUKE: Physically remove blocking elements via JS
        try:
            await self.page.evaluate("""
                const selectors = ['.m-modal', '.overlay', '[class*="backdrop"]', '.dialog-wrap', '.sg-confirm-cancel-modal-v2'];
                selectors.forEach(sel => {
                    document.querySelectorAll(sel).forEach(el => {
                        console.log('Nuking element: ' + sel);
                        el.remove();
                    });
                });
            """)
        except: pass

        # 2. Handle initial load screen if present
        try:
            loader_selectors = [
                ".app-init-loader-wrap", ".m-loader", ".loading-wrap", ".m-loading-mask",
                ".app-loading", "#app-loading", ".loading-container", ".page-loader"
            ]

            for _ in range(max_attempts):
                loader = self.page.locator(", ".join(loader_selectors)).filter(has=self.page.locator(":visible")).first
                count = await loader.count()
                if count > 0:
                    try:
                        self._log(f"DEBUG: Initial loader detected ({count} elements). Waiting for hydration...")
                        await loader.wait_for(state="hidden", timeout=7000)
                        break
                    except:
                        self._log("WARNING: Loader timeout. Attempting Force-Removal via JS...")
                        await self.hide_init_loader()
                        await asyncio.sleep(1)
                else:
                    break
        except Exception as e:
            self._log(f"DEBUG: Loader check exception: {e}")

        try:
            # Look for common WAP close buttons or Regional selectors
            overlay_selectors = [
                ".m-icon-close", ".dialog-close", ".m-modal-close", ".close-icon", ".close-btn",
                ":has-text('Nigeria')", ":has-text('Confirm')", ":has-text('OK')",
                ".sg-confirm-cancel-modal-v2 button"
            ]

            # Iterate and click all visible overlays
            found_any = False
            for selector in overlay_selectors:
                try:
                    elements = self.page.locator(selector).filter(has=self.page.locator(":visible"))
                    count = await elements.count()
                    if count > 0:
                        # Click only the first one to avoid loops if it doesn't disappear
                        await elements.first.click(force=True)
                        self._log(f"DEBUG: Dismissed overlay element: {selector}")
                        found_any = True
                except: continue

            if not found_any:
                self._log("DEBUG: No common overlays detected.")
            else:
                await asyncio.sleep(1)
        except Exception as e:
            self._log(f"DEBUG: Overlay check bypassed: {e}")

        # Dismiss background focus
        try: await self.page.mouse.click(0, 0)
        except: pass

    async def verify_auth_and_secure_artifacts(self, fatal: bool = True):
        """V5.34: Verify session state & rescue artifacts on failure."""
        self._log("DEBUG: Verifying session state...")
        try:
            # V5.34: Stabilize before checking
            await self.stabilize_environment()

            # Check for elements that PROVE we are logged in
            indicators = [
                ".icon-profile:visible", ".m-balance:visible",
                ":has-text('Deposit')", "a[href*='/deposit']:visible",
                ":has-text('Logout')", ":has-text('Log out')", ".m-user-info"
            ]
            logged_in_indicator = self.page.locator(", ".join(indicators)).first

            # Wait up to 15 seconds for the WAP framework to settle
            await logged_in_indicator.wait_for(state="visible", timeout=15000)
            self._log("DEBUG: Titan Auth SUCCESS. Session is fully valid.")

            # Save fresh state upon success
            fresh_state = await self.context.storage_state()
            self.save_storage_state(fresh_state)
            return True

        except Exception as e:
            if not fatal:
                self._log(f"WARNING: Session verification failed: {e}. Fallback possible.")
                return False

            self._log(f"CRITICAL: Titan Auth failed ({e}). Session invalid or rejected.")

            # 3. MANDATORY ARTIFACT RESCUE
            os.makedirs("artifacts", exist_ok=True)

            self._log("DEBUG: Saving fatal error artifacts before exit...")
            await self.page.screenshot(path="artifacts/titan_auth_fatal_error.png", full_page=True)

            content = await self.page.content()
            with open("artifacts/titan_auth_fatal_error.html", "w", encoding="utf-8") as f:
                f.write(content)

            # Now that artifacts are safe, exit cleanly so GitHub Actions can upload them
            sys.exit(1)

    async def human_jiggle(self):
        """V5.30: Human behavior simulation - Small scroll."""
        self._log("DEBUG: Performing human jiggle (scroll down/up)...")
        try:
            await self.page.mouse.wheel(0, 200)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await self.page.mouse.wheel(0, -200)
            await asyncio.sleep(0.5)
        except: pass

    async def hide_init_loader(self):
        """V5.21: Immediately hide the loader when state is 'Ready'."""
        self._log("DEBUG: Force hiding initial loader (Ready state reached).")
        try:
            await self.page.evaluate("""
                const selectors = [
                    '.app-init-loader-wrap', '.m-loader', '.loading-wrap', '.m-loading-mask',
                    '.app-loading', '#app-loading', '.loading-container', '.page-loader',
                    '.m-loading', '.loading', '.app-loader-wrap'
                ];
                selectors.forEach(sel => {
                    const elements = document.querySelectorAll(sel);
                    elements.forEach(el => {
                        el.style.display = 'none';
                        el.style.opacity = '0';
                        el.style.visibility = 'hidden';
                        el.style.pointerEvents = 'none';
                        el.style.zIndex = '-1';
                    });
                });
            """)
        except: pass

    async def modal_auth_system_v41(self) -> bool:
        """V4.1: Game-Route Bypass Protocol."""
        self._log("DEBUG: Executing V4.1 Modal-Auth (Game-Route Bypass)...")
        try:
            # Step A: Navigate DIRECTLY to the game (Bypass /livescore router)
            target = "https://www.football.com/ng/m/games/spin-da-bottle"
            self._log(f"DEBUG: Navigating directly to {target}...")
            await self.page.goto(target, wait_until="networkidle")

            # Step B: Settlement & DOM-NUKE
            await self.stabilize_environment()
            self._log(f"DEBUG: Settled on URL: {self.page.url}")

            # Step C: Game-Page Omni-Trigger
            self._log("DEBUG: Triggering Login from Game Page...")

            # V4.1 Omni-Selector (Prioritized for Game Page Header)
            omni_sel = "button:has-text('Login'), a:has-text('Login'), .header-login, .m-btn-login, .icon-profile"
            login_trigger = self.page.locator(omni_sel).filter(has=self.page.locator(":visible")).first

            drawer_opened = False
            if await login_trigger.count() > 0:
                self._log(f"DEBUG: Game-Page Trigger found. Clicking...")
                await login_trigger.click(force=True)
                # CRITICAL: Wait 2 seconds for Vue.js modal animation
                await asyncio.sleep(2)

                # Verify if form is visible
                phone_sel = "input[type='tel']:visible, input[placeholder*='Mobile']:visible, input[name='phone']:visible"
                if await self.page.locator(phone_sel).count() > 0:
                    self._log("DEBUG: Login modal visible.")
                    drawer_opened = True

            # Fallback: Tiered Absolute Path Override
            if not drawer_opened:
                self._log("WARNING: Game-Page Trigger failed. Forcing Absolute Login paths...")
                login_paths = ["https://www.football.com/ng/m/login", "https://www.football.com/ng/login"]
                for path in login_paths:
                    try:
                        await self.page.goto(path, wait_until="networkidle")
                        await asyncio.sleep(2)
                        await self.stabilize_environment()
                        if await self.page.locator("input[type='tel']:visible").count() > 0:
                            drawer_opened = True
                            break
                    except: continue

            if not drawer_opened:
                 self._log("DEBUG: Redirection loop detected. Breaking via JS Override...")
                 await self.page.evaluate("window.location.href = '/ng/m/login'")
                 await asyncio.sleep(3)
                 await self.stabilize_environment()

            # Step D: Wait for Credentials form
            self._log("DEBUG: Waiting for the login form to render...")
            phone_sel = "input[type='tel']:visible, input[placeholder*='Mobile']:visible, input[name='phone']:visible"
            phone_input = self.page.locator(phone_sel).first

            # If not visible, try one more stabilize
            if await phone_input.count() == 0:
                await self.stabilize_environment()

            await phone_input.wait_for(state="visible", timeout=15000)

            # Step E: Human-style credential entry
            self._log("DEBUG: Entering credentials...")
            await phone_input.click(force=True)
            await self.keyboard_type_manual(self.phone)

            password_sel = "input[type='password']:visible"
            await self.page.locator(password_sel).first.fill(self.password)

            # Step F: Submit via visible button
            self._log("DEBUG: Submit clicked.")
            submit_btn = "button.btn-primary:visible, button[type='submit']:visible, .m-login-btn:visible"
            await self.page.locator(submit_btn).first.click(force=True)

            # Mandatory Success Check
            self._log("DEBUG: Waiting for authentication verification (5-10s)...")
            await asyncio.sleep(10)

            if await self.page.locator(":has-text('Login'), :has-text('Log In')").filter(has=self.page.locator(":visible")).first.is_visible():
                # Final check for positive indicators
                indicators = [".icon-profile:visible", ".m-balance:visible", ":has-text('Deposit')"]
                if await self.page.locator(", ".join(indicators)).first.count() > 0:
                    self._log("DEBUG: LOGIN SUCCESS confirmed.")
                    return True
                self._log("CRITICAL: Login text still visible. Modal Auth FAILED.")
                await self.capture_failure("v41_login_fail")
                return False
            else:
                self._log("DEBUG: LOGIN SUCCESS confirmed.")
                return True

        except Exception as e:
            self._log(f"ERROR: V4.1 Modal Auth crashed: {e}")
            await self.capture_failure("v41_crash")
            return False

    async def keyboard_type_manual(self, text: str):
        for char in text:
            await self.page.keyboard.type(char, delay=random.randint(50, 150))
            await asyncio.sleep(random.uniform(0.01, 0.05))

    def save_storage_state(self, state: Dict[str, Any]):
        """Immortal Session: Persist Session State to MongoDB."""
        if self.collection is None: return
        try:
            # V4.1 Alignment: Upserting current context to titan_auth
            self.collection.update_one(
                {"id": "titan_auth"},
                {"$set": {"state": state, "updated_at": time.time()}},
                upsert=True
            )
            os.makedirs("artifacts", exist_ok=True)
            with open("artifacts/storage_state.json", "w") as f:
                json.dump(state, f)
            self._log("DEBUG: Saved immortal storage_state to MongoDB (titan_auth).")
        except: pass

    async def login(self) -> bool:
        """V5.33 Failsafe Repair: Sequential Auth Verification."""
        self._log("DEBUG: Starting Titan-Stealth (FAILSAFE REPAIR)...")
        await self.setup_db()

        # Step 1: Load Persistent Session
        state = self.load_storage_state()
        await self.setup_browser(storage_state=state)

        try:
            # Step 2: Session Check & Front-Door Stabilization
            await self.page.goto(self.home_url, wait_until="networkidle")
            await self.stabilize_environment()

            # Check if session is valid
            # If we see Logout or Profile or Deposit, we are logged in.
            # If we see Login/Log In, we are NOT logged in.
            is_logged_in = False
            try:
                login_indicators = [":has-text('Login')", ":has-text('Log In')"]
                login_btn = self.page.locator(", ".join(login_indicators)).filter(has=self.page.locator(":visible")).first

                # Wait briefly to see if login button appears
                if await login_btn.count() > 0 and await login_btn.is_visible():
                    self._log("DEBUG: Login button detected. Not logged in.")
                    is_logged_in = False
                else:
                    # Check for positive indicators
                    indicators = [".icon-profile:visible", ".m-balance:visible", ":has-text('Deposit')"]
                    pos_indicator = self.page.locator(", ".join(indicators)).first
                    if await pos_indicator.count() > 0:
                        is_logged_in = True
                        self._log("DEBUG: Positive auth indicators found.")
            except: pass

            if is_logged_in:
                self._log("DEBUG: Session valid via persistence.")
                # Pass fatal=False to allow fallback if verification fails
                if await self.verify_auth_and_secure_artifacts(fatal=False):
                    return True
                self._log("DEBUG: Persistence verification failed. Proceeding to manual fallback.")

            # Step 3: Fallback to Manual Validated Login (Immortal Session expired)
            self._log("WARNING: Persistent session expired. Triggering Manual Re-Validation...")
            await self.modal_auth_system_v41()

            # V5.33: Final Verification Gate
            return await self.verify_auth_and_secure_artifacts()
        except SystemExit:
            raise
        except Exception as e:
            self._log(f"ERROR: Login cycle crashed: {e}")
            return False

    async def capture_failure(self, name: str):
        try:
            os.makedirs("artifacts", exist_ok=True)
            await self.page.screenshot(path=f"artifacts/{name}.png")
            content = await self.page.content()
            with open(f"artifacts/{name}.html", "w", encoding="utf-8") as f: f.write(content)
        except: pass

    async def close(self):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()
        if self.db_client: self.db_client.close()
