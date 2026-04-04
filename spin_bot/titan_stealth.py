import os
import asyncio
import json
import time
import random
import requests
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

    async def _get_firebase_token(self) -> bool:
        """V5.29.1: Registers Firebase installation for project 'footballdotcom-78535'."""
        self._log("DEBUG: Executing Firebase Handshake...")
        try:
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.firebase_api_key
            }
            payload = {"appId": "1:753470331102:web:ae7465077d2fa908d70a4f", "authVersion": "FIS_v2"}

            # Using requests for simple handshake
            res = requests.post(self.firebase_url, json=payload, headers=headers, timeout=10)
            if res.status_code in [200, 201]:
                data = res.json()
                self.fid = data.get("fid")
                self.firebase_token = data.get("authToken", {}).get("token")
                self._log(f"DEBUG: Firebase Handshake Success.")
                return True
            else:
                self._log(f"DEBUG: Firebase Registration failed (Status: {res.status_code})")
                return False
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
            res = requests.post(self.api_login_url, json=payload, headers=headers, timeout=10)
            if res.status_code == 200:
                token = res.json().get("data", {}).get("loginToken")
                self._log("DEBUG: WAP API Login Success.")
                return token
        except Exception as e:
            self._log(f"ERROR: WAP API Login failed: {e}")
        return None

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

        # Inject region and potentially auth token manually into cookies/localStorage
        await self.context.add_cookies([{
            "name": "region", "value": "NG", "domain": "www.football.com", "path": "/", "expires": time.time() + 31536000
        }])

        self.page = await self.context.new_page()

        # V5.21 UI Sensitivity logic
        await self._apply_ui_sensitivity()

        if stealth:
            try: await stealth(self.page)
            except: pass

        self.page.set_default_timeout(15000)

    async def _apply_ui_sensitivity(self):
        self._log("DEBUG: Applying V5.21 UI Sensitivity Suite...")
        await self.page.add_init_script("""
            (function() {
                // 1. Asset Resilience (Preconnect & DNS-Prefetch)
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
                            // Fatal Error UI
                            const banner = document.createElement('div');
                            banner.style = "position:fixed;top:0;left:0;width:100%;background:red;color:white;z-index:10000;text-align:center;padding:10px;";
                            banner.innerText = "Fatal Error: Critical UI assets failed to load.";
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

                // 4. Modal Stacking & Auth Listener
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
        """V5.29.1: Waits for critical network config response to ensure Vue is ready."""
        self._log("DEBUG: Waiting for Vue.js Hydration (factsCenter/recommend/configs)...")
        try:
            await self.page.wait_for_response(lambda r: "factsCenter/recommend/configs" in r.url, timeout=15000)
            self._log("DEBUG: Vue.js Hydration Complete.")
        except:
            self._log("WARNING: Vue.js Hydration timeout. Proceeding with caution.")

    async def hide_init_loader(self):
        """V5.21.1: Standard Transition - Hide initial loader when ready."""
        try:
            await self.page.evaluate("""() => {
                const loader = document.querySelector('.app-init-loader-wrap');
                if (loader) loader.style.display = 'none';
            }""")
            self._log("DEBUG: App Init Loader hidden.")
        except: pass

    async def login(self) -> bool:
        self._log("DEBUG: Starting Project Titan-Stealth Login (FIREBASE WAP PROTOCOL)...")
        await self.setup_db()

        # 1. Attempt API Login first to bypass UI hurdles
        login_token = await self._api_login_wap()

        if login_token:
            # Construct Storage State with token
            state = {
                "cookies": [{"name": "loginToken", "value": login_token, "domain": ".football.com", "path": "/"}],
                "origins": [{
                    "origin": "https://www.football.com",
                    "localStorage": [{"name": "patron:id:accesstoken", "value": login_token}]
                }]
            }
            await self.setup(storage_state=state)
            self.save_storage_state(state)
            return True

        # 2. Fallback to existing persistent state
        state = self.load_storage_state()
        await self.setup(storage_state=state)

        try:
            await self.page.goto(self.login_url, wait_until="networkidle")
            if "/me" in self.page.url or await self.page.locator(".m-balance").is_visible():
                self._log("DEBUG: Session restored from MongoDB.")
                return True

            self._log("CRITICAL: WAP API and Persistent state both failed.")
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
