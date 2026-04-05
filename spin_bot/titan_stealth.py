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
        self.manual_login_url = "https://www.football.com/ng/m/login"
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

    def load_storage_state(self) -> Optional[Dict[str, Any]]:
        """V5.31.1: Local Storage State Recovery."""
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
                doc = self.collection.find_one({"id": "titan_stealth_session"})
                if doc and "storage_state" in doc:
                    self._log("DEBUG: Loaded storage_state from MongoDB.")
                    return doc["storage_state"]
            except: pass
        return None

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
        """V5.32.1: Header Sync Restoration (Origin/Referer fix)."""
        self._log("DEBUG: Executing Firebase Handshake (Header Sync)...")

        identity = self.load_firebase_identity()
        if identity and identity.get("refresh_token"):
            self.fid = identity["fid"]
            self.refresh_token = identity["refresh_token"]
            self._log("DEBUG: Reusing persistent Firebase Identity.")

        try:
            # V5.32.1: Added Origin and Referer to solve 400 error
            headers = {
                "Content-Type": "application/json",
                "x-goog-api-key": self.firebase_api_key,
                "x-firebase-client": "firebase-js/9.1.0",
                "Origin": "https://www.football.com",
                "Referer": "https://www.football.com/"
            }
            payload = {
                "appId": "1:753470331102:web:ae7465077d2fa908d70a4f",
                "authVersion": "FIS_v2",
                "sdkVersion": "w:10.13.0"
            }

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

                    self._log(f"DEBUG: Firebase Handshake Success.")
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

        # V5.32.1: Pre-emptive cookie injection to solve "UI Blind" and location popup
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

    async def manual_ui_login_fallback(self) -> bool:
        """V5.32.1: Human-style UI login fallback (Direct Route Fix)."""
        self._log("DEBUG: Starting Manual UI Login Fallback (Direct Route Fix)...")
        try:
            # V5.32.1: Navigate directly to /login subpath
            await self.page.goto(self.manual_login_url, wait_until="networkidle")

            # Use raw input targeting with human-like typing
            phone_sel = "input[type='tel']"
            # V5.32.1: Increased timeout to 20000ms for heavy Vue hydration
            await self.page.wait_for_selector(phone_sel, state="visible", timeout=20000)

            await self.page.locator(phone_sel).first.click(force=True)
            await self.page.keyboard.type(self.phone, delay=150)

            await self.page.locator("input[type='password']").first.click(force=True)
            await self.page.keyboard.type(self.password, delay=150)

            await self.page.locator("button.login-btn, button.btn-primary:has-text('Login')").first.click(force=True)

            try:
                await self.page.wait_for_url("**/me", timeout=15000)
                self._log("DEBUG: Manual UI Login Success.")
                state = await self.context.storage_state()
                self.save_storage_state(state)
                return True
            except:
                await self.capture_failure("manual_login_fail")
                return False
        except Exception as e:
            self._log(f"ERROR: Manual UI fallback failed: {e}")
            return False

    def save_storage_state(self, state: Dict[str, Any]):
        if self.collection is None: return
        try:
            self.collection.update_one(
                {"id": "titan_stealth_session"},
                {"$set": {"storage_state": state, "updated_at": time.time()}},
                upsert=True
            )
            os.makedirs("artifacts", exist_ok=True)
            with open("artifacts/storage_state.json", "w") as f:
                json.dump(state, f)
            self._log("DEBUG: Saved storage_state to MongoDB and artifacts.")
        except: pass

    async def login(self) -> bool:
        self._log("DEBUG: Starting Titan-Stealth (DIRECT ROUTE & HEADER SYNC)...")
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

            # Step 2: Manual UI Fallback (Direct Route Correction)
            return await self.manual_ui_login_fallback()
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
