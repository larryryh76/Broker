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
        self.api_login_url = "https://www.football.com/api/ng/users/login"
        self.firebase_url = "https://firebaseinstallations.googleapis.com/v1/projects/footballdotcom-78535/installations"
        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.phone = os.getenv("FOOTBALL_NG_LOGIN")
        self.password = os.getenv("FOOTBALL_NG_PASS")
        self.firebase_api_key = os.getenv("FIREBASE_API_KEY", "AIzaSyAs-J2n8Y9Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y5Y")
        self.db_client = None
        self.db = None
        self.collection = None
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.execution_log = []
        self.firebase_token = None
        self.fid = None
        self.refresh_token = None

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

    def load_firebase_identity(self) -> Optional[Dict[str, Any]]:
        if self.collection is None: return None
        try:
            doc = self.collection.find_one({"id": "firebase_identity"})
            if doc is not None:
                self._log("DEBUG: Loaded Firebase identity from MongoDB.")
                return doc
        except: pass
        return None

    def save_firebase_identity(self, fid: str, refresh_token: str):
        if self.collection is None: return
        try:
            self.collection.update_one(
                {"id": "firebase_identity"},
                {"$set": {"fid": fid, "refresh_token": refresh_token, "updated_at": time.time()}},
                upsert=True
            )
            self._log("DEBUG: Saved Firebase identity to MongoDB.")
        except: pass

    async def _get_firebase_token(self) -> bool:
        """V5.30.1: Restored Firebase Handshake with Identity Persistence."""
        self._log("DEBUG: Executing Firebase Handshake Restoration...")

        identity = self.load_firebase_identity()
        if identity and identity.get("refresh_token"):
            self.fid = identity["fid"]
            self.refresh_token = identity["refresh_token"]
            self._log("DEBUG: Reusing persistent Firebase Identity.")

        try:
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.firebase_api_key,
                "x-firebase-client": "firebase-js/9.1.0"
            }
            payload = {
                "appId": "1:753470331102:web:ae7465077d2fa908d70a4f",
                "authVersion": "FIS_v2"
            }

            # Use standalone start for playwright object if not initialized
            standalone_pw = None
            if not self.playwright:
                standalone_pw = await async_playwright().start()
                pw_obj = standalone_pw
            else:
                pw_obj = self.playwright

            try:
                request_context = await pw_obj.request.new_context()
                res = await request_context.post(self.firebase_url, data=payload, headers=headers)

                if res.status in [200, 201]:
                    data = await res.json()
                    self.fid = data.get("fid")
                    self.firebase_token = data.get("authToken", {}).get("token")
                    self.refresh_token = data.get("refreshToken")

                    if self.fid and self.refresh_token:
                        self.save_firebase_identity(self.fid, self.refresh_token)

                    self._log(f"DEBUG: Firebase Handshake Success. FID Secure.")
                    return True
                else:
                    self._log(f"DEBUG: Firebase Registration failed (Status: {res.status}).")
                    return False
            finally:
                if standalone_pw:
                    await standalone_pw.stop()
        except Exception as e:
            self._log(f"ERROR: Firebase Handshake crash: {e}")
            return False

    async def _api_login_wap(self) -> Optional[str]:
        """V5.29.1: Direct API Login using Firebase-authenticated WAP protocol."""
        if not self.firebase_token:
            if not await self._get_firebase_token(): return None

        self._log("DEBUG: Performing Direct WAP API Login...")
        try:
            headers = {
                "x-platform": "WAP",
                "x-app-id": "1:753470331102:web:ae7465077d2fa908d70a4f",
                "Authorization": f"Bearer {self.firebase_token}",
                "Content-Type": "application/json",
                "Referer": "https://www.football.com/ng/m/independent_login"
            }
            payload = {
                "phone": self.phone,
                "password": self.password,
                "countryCode": "Nigeria",
                "fid": self.fid
            }

            standalone_pw = None
            if not self.playwright:
                standalone_pw = await async_playwright().start()
                pw_obj = standalone_pw
            else:
                pw_obj = self.playwright

            try:
                request_context = await pw_obj.request.new_context()
                res = await request_context.post(self.api_login_url, data=payload, headers=headers)

                if res.status == 200:
                    data = await res.json()
                    token = data.get("data", {}).get("loginToken")
                    if token:
                        self._log("DEBUG: WAP API Login Success.")
                        return token
                self._log(f"DEBUG: WAP API Login failed (Status: {res.status}).")
            finally:
                if standalone_pw:
                    await standalone_pw.stop()
        except Exception as e:
            self._log(f"ERROR: WAP API Login failed: {e}")
        return None

    async def setup_browser(self, storage_state: Optional[Dict[str, Any]] = None):
        if not self.playwright:
            self.playwright = await async_playwright().start()

        self.browser = await self.playwright.chromium.launch(headless=True)

        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 14; CPH2641) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.119 Mobile Safari/537.36",
            viewport={'width': 390, 'height': 844},
            is_mobile=True,
            has_touch=True,
            locale="en-NG",
            timezone_id="Africa/Lagos",
            geolocation={"latitude": 6.5244, "longitude": 3.3792},
            permissions=["geolocation"],
            storage_state=storage_state,
            ignore_https_errors=True
        )

        # Pre-emptive region cookie to prevent Location modal
        await self.context.add_cookies([{
            "name": "region", "value": "NG", "domain": ".football.com", "path": "/"
        }])

        self.page = await self.context.new_page()
        await self._apply_ui_sensitivity()

        if stealth:
            try: await stealth(self.page)
            except: pass

        self.page.set_default_timeout(15000)

    async def _apply_ui_sensitivity(self):
        self._log("DEBUG: Injecting V5.21 UI Sensitivity Suite...")
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

                // 2. Asset Retry Hook
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
                            const banner = document.createElement('div');
                            banner.style = "position:fixed;top:0;left:0;width:100%;background:red;color:white;z-index:10000;text-align:center;padding:10px;";
                            banner.innerText = "Fatal Error: Critical assets failed to load.";
                            document.body.appendChild(banner);
                        }
                    }
                }, true);

                // 3. Theme & Loader Styling
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

                // 4. Global Auth Listener
                const originalFetch = window.fetch;
                window.fetch = async (...args) => {
                    const res = await originalFetch(...args);
                    if (res.status === 401) triggerLoginModal();
                    return res;
                };

                function triggerLoginModal() {
                    if (document.getElementById('omni-login-modal')) return;
                    const modal = document.createElement('div');
                    modal.id = 'omni-login-modal';
                    modal.innerHTML = `
                        <div class="modal-backdrop" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;z-index:1052;">
                            <div class="modal-content" style="background:white;padding:20px;border-radius:8px;text-align:center;z-index:1055;">
                                <p style="color:red;font-weight:bold;">Error! Please login to start game.</p>
                                <button onclick="window.location.href='/ng/m/independent_login'" style="background:#007bff;color:white;padding:10px;margin:5px;border-radius:4px;border:none;">Login</button>
                                <button onclick="window.location.href='/ng/m/'" style="background:#6c757d;color:white;padding:10px;margin:5px;border-radius:4px;border:none;">Exit</button>
                            </div>
                        </div>`;
                    document.body.appendChild(modal);
                }

                const observer = new MutationObserver(() => {
                    applyThemeStyle();
                    document.querySelectorAll('.modal-backdrop').forEach((b, i) => b.style.zIndex = (1052 + (i*10)).toString());
                    document.querySelectorAll('.modal-content').forEach((c, i) => c.style.zIndex = (1055 + (i*10)).toString());
                });
                observer.observe(document.body, { childList: true, subtree: true });

                setInterval(() => {
                    if (document.body.innerText.includes('Error! Please login to start game')) triggerLoginModal();
                }, 2000);
            })();
        """)

    async def wait_for_vue_hydration(self):
        self._log("DEBUG: Waiting for Vue.js Hydration (factsCenter/configs)...")
        try:
            await self.page.wait_for_response(lambda r: "factsCenter/recommend/configs" in r.url, timeout=15000)
            self._log("DEBUG: Vue.js Hydration Complete.")
        except:
            self._log("WARNING: Vue.js Hydration timeout.")

    async def hide_init_loader(self):
        try:
            await self.page.evaluate("document.querySelector('.app-init-loader-wrap').style.display = 'none'")
        except: pass

    async def login(self) -> bool:
        self._log("DEBUG: Starting Titan-Stealth (FIREBASE HANDSHAKE RESTORATION)...")
        await self.setup_db()

        # Step 1: Direct API Login (WAP)
        login_token = await self._api_login_wap()

        if login_token:
            state = {
                "cookies": [
                    {"name": "loginToken", "value": login_token, "domain": ".football.com", "path": "/"},
                    {"name": "region", "value": "NG", "domain": ".football.com", "path": "/"}
                ],
                "origins": [{
                    "origin": "https://www.football.com",
                    "localStorage": [{"name": "patron:id:accesstoken", "value": login_token}]
                }]
            }
            await self.setup_browser(storage_state=state)
            self.save_storage_state(state)
            return True

        # Fallback to persistent state
        state = self.load_storage_state()
        await self.setup_browser(storage_state=state)

        try:
            await self.page.goto(self.login_url, wait_until="networkidle")
            if "/me" in self.page.url or await self.page.locator(".m-balance").is_visible():
                self._log("DEBUG: Session valid via persistence.")
                return True
            return False
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
