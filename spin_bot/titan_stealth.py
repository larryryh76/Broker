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
        self.home_url = "https://www.football.com/ng/m/"
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
        await self.context.add_cookies([{
            "name": "region", "value": "NG", "domain": ".football.com", "path": "/"
        }])

        self.page = await self.context.new_page()

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
                const observer = new MutationObserver(() => {
                    const theme = document.documentElement.getAttribute('data-theme') || 'light';
                    const brand = window.BRAND_NAME || 'football';
                    const loader = document.querySelector('.app-init-loader-wrap');
                    const spinner = document.querySelector('.spinner-icon'); // Hypothetical selector

                    if (loader) {
                        if (theme === 'light') {
                            loader.style.backgroundColor = '#f4f4f4';
                            if (spinner) spinner.style.backgroundColor = '#e0e1e2';
                        } else {
                            loader.style.backgroundColor = (brand === 'Encore') ? '#100e26' : '#000000';
                        }
                    }

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
                observer.observe(document.body, { childList: true, subtree: true });
            })();
        """)

    async def hard_anchor_navigation(self, target_url: str, max_attempts: int = 3):
        """V5.30: Bypass & Blast Navigation Lock."""
        # Use direct search-proxied bypass link if provided in prompt
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

    async def human_jiggle(self):
        """V5.30: Human behavior simulation - Small scroll."""
        self._log("DEBUG: Performing human jiggle (scroll down/up)...")
        try:
            await self.page.mouse.wheel(0, 200)
            await asyncio.sleep(random.uniform(0.5, 1.5))
            await self.page.mouse.wheel(0, -200)
            await asyncio.sleep(0.5)
        except: pass

    async def blind_clearance(self):
        """V5.30: Overlay Killer - Force clear ghost layers."""
        self._log("DEBUG: Executing Blind Clearance (Overlay Killer)...")
        selectors = [".m-icon-close", ".close-btn", ".m-modal-close", ".close-icon"]
        for sel in selectors:
            try:
                loc = self.page.locator(f"{sel}:visible")
                if await loc.count() > 0:
                    self._log(f"DEBUG: Blasting overlay: {sel}")
                    await loc.first.click(force=True)
                    await asyncio.sleep(1)
            except: pass
        # Dismiss background focus
        try: await self.page.mouse.click(0, 0)
        except: pass

    async def _handle_overlays(self):
        """V5.18: Splash & Overlay Handling Logic."""
        self._log("DEBUG: Checking for Regional Splash & Overlays...")
        try:
            # Detect Nigeria in Regional Splash
            nigeria_btn = self.page.locator("div.m-list-item[data-op='region_country-item']:has-text('Nigeria')")
            if await nigeria_btn.is_visible():
                self._log("DEBUG: Regional Splash detected. Selecting Nigeria...")
                await nigeria_btn.click(force=True)
                await asyncio.sleep(2)

            # Close Blocking Modals/Ads
            close_btn = self.page.locator(".m-icon-close, .close-btn, .modal-close").first
            if await close_btn.is_visible():
                self._log("DEBUG: Closing ad overlay...")
                await close_btn.click(force=True)
                await asyncio.sleep(1)
        except: pass

    async def navigation_guardian(self, max_attempts: int = 3):
        """V5.15 Guardian: Prevent /livescore redirect loops."""
        for i in range(max_attempts):
            if "/livescore" in self.page.url:
                self._log(f"WARNING: Livescore redirect detected (Attempt {i+1}). Re-navigating to Game...")
                await asyncio.sleep(2)
                await self.page.goto(self.game_url, wait_until="networkidle")
            else:
                break

    async def hide_init_loader(self):
        try:
            await self.page.evaluate("document.querySelector('.app-init-loader-wrap').style.display = 'none'")
        except: pass

    async def modal_auth_system_v41(self) -> bool:
        """V4.1: Re-implemented Modal-Auth Trigger System."""
        self._log("DEBUG: Executing V4.1 Modal-Auth Trigger Sequence...")
        try:
            # Step A: Navigate to Home
            await self.page.goto(self.home_url)
            await self.page.wait_for_load_state("networkidle")

            # Step B (The Trigger): CLICK Login to make modal appear
            self._log("DEBUG: Clicking Login trigger...")
            await self.page.locator("text=/^(Log In|Login)$/i:visible").first.click(force=True)

            # Step C (The Modal): Wait for password selector
            self._log("DEBUG: Waiting for Login Modal...")
            password_sel = "input[type='password']:visible"
            await self.page.wait_for_selector(password_sel, state="visible", timeout=15000)

            # Step D (Human Typing): Fill credentials
            phone_sel = "input[type='tel']:visible, input[placeholder*='Phone']:visible, input[placeholder*='Email']:visible"
            await self.page.locator(phone_sel).first.click(force=True)
            await self.keyboard_type_manual(self.phone)

            await self.page.locator(password_sel).first.click(force=True)
            await self.keyboard_type_manual(self.password)

            # Step E (Submission): Submit Modal
            submit_btn = "button.login-btn:visible, button[type='submit']:visible, button:has-text('Login'):visible"
            await self.page.locator(submit_btn).last.click(force=True)

            # Mandatory Success Check
            self._log("DEBUG: Verifying login success...")
            await asyncio.sleep(10)

            if await self.page.locator("text=/^(Log In|Login)$/i").first.is_visible():
                self._log("CRITICAL: Login text still visible. Modal Auth FAILED.")
                await self.capture_failure("v41_login_fail")
                return False
            else:
                self._log("DEBUG: LOGIN SUCCESS confirmed via V4.1 Modal Trigger.")
                state = await self.context.storage_state()
                self.save_storage_state(state)
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
        """V5.22: Golden Path with WAP Redirect Bypass."""
        self._log("DEBUG: Starting Titan-Stealth (V5.22 GOLDEN PATH)...")
        await self.setup_db()

        # Step 1: Load Persistent Session
        state = self.load_storage_state()
        await self.setup_browser(storage_state=state)

        try:
            # Step 2: Modal Trap Detection & Front-Door Stabilization
            self._log("DEBUG: Checking for Modal Trap...")
            modal = self.page.locator(".modal-content")

            is_trapped = False
            try:
                await modal.wait_for(state="visible", timeout=5000)
                is_trapped = True
            except: pass

            if is_trapped:
                self._log("DEBUG: Modal Trap detected. Forcing navigation to clear state...")
                await self.page.goto(self.home_url, wait_until="domcontentloaded")
                await asyncio.sleep(3)
                self._log(f"DEBUG: Settled on WAP URL: {self.page.url}")
            else:
                await self.page.goto(self.home_url, wait_until="networkidle")
                await self._handle_overlays()

            # Check if session is valid (Login button missing)
            login_trigger = self.page.locator("text=/^(Log In|Login)$/i:visible").first
            if not await login_trigger.is_visible():
                self._log("DEBUG: Session valid via persistence.")
                fresh_state = await self.context.storage_state()
                self.save_storage_state(fresh_state)
                return True

            # Step 3: V5.22 WAP Overlay Login Fallback
            success = await self.modal_auth_system_v41()
            if success:
                fresh_state = await self.context.storage_state()
                self.save_storage_state(fresh_state)
            return success
        except: return False

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
