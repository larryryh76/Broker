import os
import asyncio
import json
import time
import random
import socketio
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
        self.websocket_url = "wss://alive-ng.football.com/socket.io/?EIO=3&transport=websocket"
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
        self.sio = None

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
        """V4.4: Restore Session State (Cookies + Origins)."""
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

    async def _init_websocket(self) -> bool:
        """V4.4 ALIVE-NG: Initiate Socket.io Handshake."""
        self._log("DEBUG: Initiating ALIVE-NG Socket.io Handshake...")
        try:
            self.sio = socketio.AsyncClient(logger=True, engineio_logger=True)

            @self.sio.event
            async def connect():
                self._log("DEBUG: ALIVE-NG WebSocket Connected.")

            @self.sio.event
            async def disconnect():
                self._log("DEBUG: ALIVE-NG WebSocket Disconnected.")

            # EIO=3 WebSocket-first handshake with realistic headers
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 14; CPH2641) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.119 Mobile Safari/537.36",
                "Origin": "https://www.football.com",
                "Referer": "https://www.football.com/"
            }

            await self.sio.connect(
                self.websocket_url,
                transports=['websocket'],
                headers=headers,
                socketio_path='socket.io'
            )
            return True
        except Exception as e:
            self._log(f"WARNING: ALIVE-NG WebSocket failed (Expected in CI/WAF): {e}")
            return False

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
            await self.keyboard_type_manual(self.phone)

            await self.page.locator("input[type='password']").first.click(force=True)
            await self.keyboard_type_manual(self.password)

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

    async def keyboard_type_manual(self, text: str):
        for char in text:
            await self.page.keyboard.type(char, delay=random.randint(50, 150))
            await asyncio.sleep(random.uniform(0.01, 0.05))

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
        self._log("DEBUG: Starting Titan-Stealth (V4.4 ALIVE-NG)...")
        await self.setup_db()

        # Step 1: Warm up ALIVE-NG WebSocket
        await self._init_websocket()

        # Step 2: Load Persistent Session
        state = self.load_storage_state()
        await self.setup_browser(storage_state=state)

        try:
            # Check if session is already valid
            await self.page.goto(self.login_url, wait_until="networkidle")
            if "/me" in self.page.url or await self.page.locator(".m-balance").is_visible():
                self._log("DEBUG: Session valid via persistence.")
                return True

            # Step 3: Manual UI Fallback
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
        if self.sio and self.sio.connected: await self.sio.disconnect()
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()
        if self.db_client: self.db_client.close()
