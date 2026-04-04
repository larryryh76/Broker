import os
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
        self.login_url = "https://www.football.com/ng/m/independent_login"
        self.api_login_url = "https://www.football.com/api/ng/auth/login"
        self.discovered_login_url = None
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

        # V5.28.1 Heuristic Filters
        self.tracker_keywords = ["google-analytics", "googletagmanager", "doubleclick", "facebook", "pixel", "analytics", "collect?"]

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
        if self.collection is None: return None
        try:
            doc = self.collection.find_one({"id": "titan_stealth_session"})
            if doc is not None and "storage_state" in doc:
                self._log("DEBUG: Loaded storage_state from MongoDB.")
                return doc["storage_state"]
        except Exception as e:
            self._log(f"DEBUG: Failed to load storage_state: {e}")
        return None

    def save_storage_state(self, state: Dict[str, Any]):
        if self.collection is None: return
        try:
            self.collection.update_one(
                {"id": "titan_stealth_session"},
                {"$set": {"storage_state": state, "updated_at": time.time()}},
                upsert=True
            )
            self._log("DEBUG: Saved storage_state to MongoDB.")
        except Exception as e:
            self._log(f"ERROR: Failed to save storage_state: {e}")

    def _is_valid_auth_endpoint(self, url: str) -> bool:
        """V5.28.1: Heuristic filter to reject trackers and prioritize real API endpoints."""
        url_lower = url.lower()
        if "football.com" not in url_lower: return False
        if any(tk in url_lower for tk in self.tracker_keywords): return False
        return any(kw in url_lower for kw in ["auth", "login", "sign-in", "api/ng/"])

    async def _on_request(self, request: Request):
        url = request.url
        if self._is_valid_auth_endpoint(url):
            self._log(f"DEBUG: Outbound Request Sniffed -> {url}")
            if request.method == "POST":
                self.discovered_login_url = url

    async def _on_response(self, response: Response):
        url = response.url
        if self._is_valid_auth_endpoint(url):
            if response.status in [401, 403]:
                self._log(f"DEBUG: Auth Response {response.status} -> {url} (Captured as dynamic endpoint)")
                self.discovered_login_url = url

    async def _on_framenavigated(self, frame):
        if frame == self.page.main_frame:
            url = self.page.url
            if "/me" in url or "/m/home" in url:
                self._log(f"DEBUG: Golden Ticket detected (URL: {url}). Saving state immediately!")
                try:
                    state = await self.context.storage_state()
                    self.save_storage_state(state)
                except: pass

    async def setup(self, storage_state: Optional[Dict[str, Any]] = None):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)

        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 14; CPH2641) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.119 Mobile Safari/537.36",
            viewport={'width': 360, 'height': 800},
            is_mobile=True,
            has_touch=True,
            locale="en-NG",
            timezone_id="Africa/Lagos",
            geolocation={"latitude": 6.5244, "longitude": 3.3792},
            permissions=["geolocation"],
            storage_state=storage_state,
            ignore_https_errors=True
        )

        await self.context.add_cookies([{
            "name": "region", "value": "NG", "domain": "www.football.com", "path": "/", "expires": time.time() + 31536000
        }])

        self.page = await self.context.new_page()

        # V5.21.1 UI Sensitivity & Dynamic Interception
        await self._apply_ui_and_interception()

        if stealth:
            try: await stealth(self.page)
            except: pass

        self.page.set_default_timeout(15000)

    async def _apply_ui_and_interception(self):
        self._log("DEBUG: Applying V5.21.1 UI Sensitivity & Interceptor Logic...")

        # Network Interception setup
        await self.page.route("**/*", lambda route: route.continue_())
        self.page.on("request", self._on_request)
        self.page.on("response", self._on_response)
        self.page.on("framenavigated", self._on_framenavigated)

        # JS Injections for V5.21 UI Enhancement
        await self.page.add_init_script("""
            (function() {
                // 1. Asset Resilience
                const domains = ['https://www.football.com', 'https://s.football.com/games/'];
                domains.forEach(d => {
                    ['preconnect', 'dns-prefetch'].forEach(rel => {
                        const link = document.createElement('link');
                        link.rel = rel; link.href = d;
                        document.head.appendChild(link);
                    });
                });

                window.addEventListener('error', function(e) {
                    const target = e.target;
                    if (target && (target.tagName === 'SCRIPT' || target.tagName === 'LINK')) {
                        const retryCount = parseInt(target.getAttribute('data-retry') || '0');
                        if (retryCount < 2) {
                            const newTarget = document.createElement(target.tagName);
                            if (target.tagName === 'SCRIPT') { newTarget.src = target.src; newTarget.async = true; }
                            else { newTarget.rel = 'stylesheet'; newTarget.href = target.href; }
                            newTarget.setAttribute('data-retry', retryCount + 1);
                            document.head.appendChild(newTarget);
                        } else {
                            // Fatal Error UI
                            const errorBanner = document.createElement('div');
                            errorBanner.style = "position:fixed;top:0;left:0;width:100%;background:red;color:white;z-index:10000;text-align:center;padding:10px;";
                            errorBanner.innerText = "Fatal Error: Critical assets failed to load.";
                            document.body.appendChild(errorBanner);
                        }
                    }
                }, true);

                // 2. Theme & Loader Styling
                function applyThemeStyle() {
                    const theme = document.documentElement.getAttribute('data-theme') || 'light';
                    const brand = window.BRAND_NAME || 'football';
                    const loader = document.querySelector('.app-init-loader-wrap');
                    if (loader) {
                        if (theme === 'light') {
                            loader.style.backgroundColor = '#f4f4f4';
                            const spinner = loader.querySelector('.spinner-icon');
                            if (spinner) spinner.style.backgroundColor = '#e0e1e2';
                        } else {
                            loader.style.backgroundColor = (brand === 'Encore') ? '#100e26' : '#000000';
                        }
                    }
                }

                const observer = new MutationObserver(() => {
                    applyThemeStyle();
                    // Z-Index Stacking
                    document.querySelectorAll('.modal-backdrop').forEach((b, i) => b.style.zIndex = (1052 + (i*10)).toString());
                    document.querySelectorAll('.modal-content').forEach((c, i) => c.style.zIndex = (1055 + (i*10)).toString());
                });
                observer.observe(document.body, { childList: true, subtree: true });

                // 3. Global Auth Listener
                const originalFetch = window.fetch;
                window.fetch = async (...args) => {
                    const response = await originalFetch(...args);
                    if (response.status === 401) triggerLoginModal();
                    return response;
                };

                function triggerLoginModal() {
                    if (document.getElementById('omni-login-modal')) return;
                    const modal = document.createElement('div');
                    modal.id = 'omni-login-modal';
                    modal.innerHTML = `
                        <div class="modal-backdrop" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:9999;">
                            <div class="modal-content" style="background:white;padding:20px;border-radius:8px;text-align:center;">
                                <p style="color:red;font-weight:bold;">Error! Please login to start game.</p>
                                <button onclick="window.location.href='/ng/m/independent_login'" style="background:#007bff;color:white;padding:10px;margin:5px;">Login</button>
                                <button onclick="window.location.href='/ng/m/'" style="background:#6c757d;color:white;padding:10px;margin:5px;">Exit</button>
                            </div>
                        </div>`;
                    document.body.appendChild(modal);
                }

                setInterval(() => {
                    if (document.body.innerText.includes('Error! Please login to start game')) triggerLoginModal();
                }, 2000);
            })();
        """)

    async def handle_region_trap(self):
        """V5.27.2: State-Machine Fix - Interaction over Removal."""
        self._log("DEBUG: Resolving Region Trap via State-Machine Transition...")
        try:
            ready_state = await self.page.evaluate("document.readyState")
            if ready_state != "complete":
                try: await self.page.wait_for_function("document.readyState === 'complete'", timeout=5000)
                except: pass

            # Preference: Clicking Nigeria to trigger hydration
            nigeria_btn = self.page.locator('div.m-list-item[data-op="region_country-item"]').filter(has_text="Nigeria").first
            try:
                await nigeria_btn.wait_for(state="visible", timeout=3000)
                await nigeria_btn.click(force=True)
                self._log("DEBUG: Selected Nigeria via native click.")
                await asyncio.sleep(5) # Hydration Sync delay
                await self.page.wait_for_load_state("networkidle")
            except:
                # Fallback to close button if list item not found
                close_btn = self.page.locator('i.m-icon-close[data-op="region-close"]')
                if await close_btn.is_visible():
                    await close_btn.click()
                    self._log("DEBUG: Closed region modal via native click.")
                    await asyncio.sleep(2)
        except Exception as e:
            self._log(f"DEBUG: Region trap handling skipped/failed: {e}")

    async def human_jitter(self):
        """V5.27.5: Human Jitter loop to trigger Vue.js hydration."""
        self._log("DEBUG: Executing Human Jitter...")
        try:
            for _ in range(3):
                await self.page.mouse.move(random.randint(0, 300), random.randint(0, 300))
                await asyncio.sleep(random.uniform(0.5, 1.5))
        except: pass

    async def hide_init_loader(self):
        """V5.21.1: Standard Transition - Hide initial loader when ready."""
        try:
            await self.page.evaluate("""() => {
                const loader = document.querySelector('.app-init-loader-wrap');
                if (loader) loader.style.display = 'none';
            }""")
            self._log("DEBUG: App Init Loader hidden.")
        except: pass

    async def api_login_fallback(self) -> bool:
        target = self.discovered_login_url or self.api_login_url
        self._log(f"DEBUG: Executing Self-Healing API Fallback -> {target}")
        try:
            payload = {"mobile": self.phone, "password": self.password, "remember": True}
            response = await self.context.request.post(target, data=payload, headers={"Referer": self.login_url})
            if response.status == 200:
                self._log("DEBUG: API Login Successful. Golden Ticket Secured.")
                state = await self.context.storage_state()
                self.save_storage_state(state)
                return True
            else:
                self._log(f"DEBUG: API Fallback failed (Status: {response.status}).")
                return False
        except Exception as e:
            self._log(f"DEBUG: API Fallback crash: {e}")
            return False

    async def login(self) -> bool:
        self._log("DEBUG: Starting Project Titan-Stealth (HEURISTIC INTERCEPTOR)...")
        await self.setup_db()
        state = self.load_storage_state()
        await self.setup(storage_state=state)

        try:
            await self.page.goto(self.login_url, wait_until="networkidle")

            # Step 1: Handle Region Trap (State-Machine Sync)
            await self.handle_region_trap()

            # Step 2: Check Login Status
            if "/me" in self.page.url or await self.page.locator(".m-balance").is_visible():
                self._log("DEBUG: Session valid via existing state.")
                return True

            self._log("DEBUG: Session invalid. Attempting UI interaction with Jitter...")
            await self.human_jitter()

            phone_sel = "input[type='tel']"
            try:
                await self.page.wait_for_selector(phone_sel, state="visible", timeout=7000)
            except:
                self._log("DEBUG: Inputs hidden. Forcing hydration via scroll...")
                await self.page.mouse.wheel(0, 500)
                await asyncio.sleep(2)
                try:
                    await self.page.wait_for_selector(phone_sel, state="visible", timeout=5000)
                except:
                    # Tab Switch Fallback
                    self._log("DEBUG: Attempting Tab Switch fallback...")
                    for tab in [".m-tabs-item", "text='Login'"]:
                        try:
                            btn = self.page.locator(tab).first
                            if await btn.is_visible(): await btn.click(force=True)
                        except: continue

                    try: await self.page.wait_for_selector(phone_sel, state="visible", timeout=5000)
                    except:
                        self._log("WARNING: UI blind. Triggering Self-Healing API Fallback.")
                        return await self.api_login_fallback()

            # Human Typing
            await self.page.locator(phone_sel).first.click(force=True)
            for char in self.phone:
                await self.page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))

            await self.page.locator("input[type='password']").first.click(force=True)
            for char in self.password:
                await self.page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))

            await self.page.locator("button.login-btn, button.btn-primary:has-text('Login')").first.click(force=True)

            try:
                await self.page.wait_for_url("**/me", timeout=10000)
                self._log("DEBUG: UI Login Verified.")
                state = await self.context.storage_state()
                self.save_storage_state(state)
                return True
            except: return await self.api_login_fallback()

        except Exception as e:
            self._log(f"CRITICAL: Interceptor flow failed: {e}")
            return await self.api_login_fallback()

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
