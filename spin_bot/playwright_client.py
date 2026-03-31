import os
import random
import asyncio
import time
import json
import gzip
from playwright.async_api import async_playwright, Page, ElementHandle, Response, Request, WebSocket
try:
    from playwright_stealth import stealth_async as stealth
except ImportError:
    stealth = None
from typing import List, Optional, Dict, Union, Any
from spin_bot.api_client import normalize_url

class PlaywrightClient:
    def __init__(self, login_url: str):
        self.login_url = login_url or "https://www.football.com"
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None
        self.game_frame = None
        self.execution_log = []
        self.network_log = []
        self.discovered_endpoints = {"history": None, "bet": None}
        self.auth_state = {
            "accessToken": os.getenv("GOLDEN_ACCESS_TOKEN", ""),
            "refreshToken": os.getenv("GOLDEN_REFRESH_TOKEN", ""),
            "puid": os.getenv("GOLDEN_PUID", ""),
            "deviceId": os.getenv("GOLDEN_DEVICE_ID", ""),
            "cf_bm": os.getenv("GOLDEN_CF_BM", "")
        }

    def _log_execution(self, message: str):
        print(message)
        self.execution_log.append(f"[{time.ctime()}] {message}")

    async def capture_failure_artifact(self, name: str):
        """V5.12.1: Robust failure documentation."""
        try:
            os.makedirs("artifacts", exist_ok=True)
            await self.page.screenshot(path=f"artifacts/{name}.png")
            content = await self.page.content()
            with open(f"artifacts/{name}.html", "w", encoding="utf-8") as f:
                f.write(content)
            self._log_execution(f"DEBUG: Saved artifacts for {name}")
        except: pass

    async def setup(self, cookies: List[Dict] = None, session_state: Dict = None):
        self.playwright = await async_playwright().start()
        launch_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
            "--disable-dev-shm-usage",
            "--disable-web-security",
            "--disable-features=IsolateOrigins,site-per-process",
            "--headless=new"
        ]
        self.browser = await self.playwright.chromium.launch(headless=True, args=launch_args)

        # V5.9.4 Mobile/Stealth Configuration
        iphone_13 = self.playwright.devices["iPhone 13"]
        iphone_13['viewport'] = {'width': 390, 'height': 844}

        proxy_server = os.getenv("PROXY_SERVER")
        proxy_config = {"server": proxy_server} if proxy_server else None
        if proxy_config and os.getenv("PROXY_USERNAME"):
            proxy_config["username"] = os.getenv("PROXY_USERNAME")
            proxy_config["password"] = os.getenv("PROXY_PASSWORD")

        self.context = await self.browser.new_context(
            **iphone_13,
            locale="en-NG",
            timezone_id="Africa/Lagos",
            ignore_https_errors=True,
            proxy=proxy_config
        )

        # V5.9.4 Anti-Redirect Header
        await self.context.set_extra_http_headers({"X-Requested-With": "com.android.browser"})

        # V5.17.0: Cross-Domain Injection (Football.com + SportyGames.com)
        if session_state and "auth_state" in session_state:
            self.auth_state.update(session_state["auth_state"])

        # V5.17.0: Map tokens to multiple domains to fix iframe auth inheritance
        domains = [".football.com", ".sportygames.com", "www.football.com"]
        if self.auth_state.get("cf_bm"):
            for domain in domains:
                cf_cookie = {
                    "name": "__cf_bm",
                    "value": self.auth_state["cf_bm"],
                    "domain": domain,
                    "path": "/",
                    "secure": True,
                    "httpOnly": True,
                    "sameSite": "None"
                }
                await self.context.add_cookies([cf_cookie])

        if cookies:
            try:
                # Mirror top-level cookies to iframe domain
                for c in cookies:
                    c_copy = c.copy()
                    c_copy["domain"] = ".sportygames.com"
                    await self.context.add_cookies([c, c_copy])
                self._log_execution("DEBUG: Cross-Domain session cookies injected.")
            except Exception as e:
                self._log_execution(f"DEBUG: Cookie injection failed: {e}")

        self.page = await self.context.new_page()

        # V5.15.0: Golden Token & Storage Injection
        storage = session_state.get("storage", {}) if session_state else {}
        local_storage = storage.get("local", {})

        # Merge Golden Tokens into LocalStorage
        if self.auth_state.get("accessToken"):
            local_storage["patron:id:accesstoken"] = self.auth_state["accessToken"]
        if self.auth_state.get("refreshToken"):
            local_storage["patron:id:refreshtoken"] = self.auth_state["refreshToken"]
        if self.auth_state.get("puid"):
            local_storage["patron:id:puid"] = self.auth_state["puid"]
        if self.auth_state.get("deviceId"):
            local_storage["deviceId"] = self.auth_state["deviceId"]

        try:
            # V5.17.0: Iframe Tunneling (localStorage Injection for all domains)
            local_storage.setdefault("keep_signed_in", "1")
            local_storage.setdefault("remember_me", "1")
            local_storage.setdefault("fcom_theme_theme", "classic")

            # Use context.add_init_script to ensure it runs on all pages AND iframes
            await self.context.add_init_script(f"""
                const local = {json.dumps(local_storage)};
                const session = {json.dumps(storage.get('session', {}))};
                if (window.location.hostname.includes('football.com') || window.location.hostname.includes('sportygames.com')) {{
                    for (const k in local) localStorage.setItem(k, local[k]);
                    for (const k in session) sessionStorage.setItem(k, session[k]);
                }}
            """)
            self._log_execution("DEBUG: V5.17 Cross-Domain Storage Tunneling active.")
        except Exception as e:
            self._log_execution(f"DEBUG: Storage injection failed: {e}")

        self.page.set_default_timeout(60000)
        self.page.on("request", self._log_request)
        self.page.on("response", self._log_response)

        if stealth:
            try: await stealth(self.page)
            except: pass
        await self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    async def login(self, retry: bool = True):
        user = os.getenv("FOOTBALL_NG_LOGIN")
        pw = os.getenv("FOOTBALL_NG_PASS")
        if not user or not pw: return
        self._log_execution(f"DEBUG: Initializing V5.16 GHOST BYPASS LOGIN...")
        try:
            # 1. Direct Login Landing
            login_url = "https://www.football.com/ng/m/independent_login"
            await self.page.goto(login_url, wait_until="networkidle")
            await self._handle_overlays()
            await self._handle_regional_splash()

            # 2. V5.16 Visible-Only Input Handling
            self._log_execution("DEBUG: Entering credentials via visible selectors...")

            # Resolve "Hidden Input" crash by targeting only visible elements
            # Step 1: Phone number
            phone_field = self.page.locator("input:visible").filter(has_text="Mobile Number").first
            if not await phone_field.is_visible():
                phone_field = self.page.locator("input[type='tel']:visible, input[placeholder*='Mobile']:visible").first

            await phone_field.fill(user)

            # Step 2: Password
            password_field = self.page.locator("input[type='password']:visible").first
            await password_field.fill(pw)

            # 5. Submission
            login_btn = self.page.locator("button.m-btn-login:visible, .m-login-btn:visible, button:has-text('Log In'):visible").first
            await login_btn.click(force=True)

            # 6. Strict Verification (User Indicator or Modal Disappearance)
            try:
                self._log_execution("DEBUG: Verifying session (30s timeout)...")
                # Wait for user profile indicator OR modal disappearance
                # wait_for_selector refactored to avoid = in CSS
                await asyncio.wait([
                    self.page.wait_for_selector(".m-user-info", state="visible"),
                    self.page.wait_for_selector("input[type='password']", state="hidden")
                ], return_when=asyncio.FIRST_COMPLETED, timeout=30000)

                self._log_execution("LOGIN SUCCESS")
            except Exception as e:
                self._log_execution(f"CRITICAL: TRUE LOGIN FAILED: {e}")
                await self.capture_failure_artifact("login_verify_fail")
                import sys
                sys.exit(1)

            await asyncio.sleep(2)
            await self._handle_overlays()
        except Exception as e:
            self._log_execution(f"CRITICAL: Login UI Error: {e}")
            await self.page.screenshot(path="artifacts/error.png")

    async def navigate_to_game(self) -> bool:
        """V5.17.0: Direct Iframe Tunneling Navigation."""
        target_url = "https://www.football.com/ng/games/spin-da-bottle"

        for attempt in range(3):
            try:
                self._log_execution(f"DEBUG: V5.17 Predator Tunneling Navigation Attempt {attempt+1}...")
                await self.page.goto(target_url, wait_until="networkidle")
                await self._handle_overlays()

                # V5.17.0: Login Modal Breaker (Iframe Check)
                self.game_frame = self.page.frame_locator("iframe[src*='sportygames']")

                try:
                    # Check for login modal INSIDE the iframe
                    login_text = self.game_frame.locator("text='Please login to start game', .m-login-btn").first
                    if await login_text.is_visible(timeout=5000):
                        self._log_execution("DEBUG: V5.17 Login Modal Breaker Triggered (In-Iframe Injection)...")
                        await self._break_iframe_login()
                except: pass

                # Verify if we are logged in
                try:
                    await self.page.wait_for_selector(".m-user-info, .m-balance", timeout=5000)
                    self._log_execution("DEBUG: Predator Session Authenticated.")
                except:
                    self._log_execution("WARNING: Session not visually verified.")

                # 4. Iframe Sync & UI Verification
                try:
                    self._log_execution("DEBUG: Waiting for Game Iframe Sync...")
                    ui_indicator = self.game_frame.locator("canvas, .history, .results, .history-list, .bet-panel").first
                    await ui_indicator.wait_for(state="visible", timeout=45000)

                    self._log_execution("IFRAME FOUND")
                    return True

                except Exception as e:
                    # Capture all iframes and log src on failure
                    iframes = await self.page.query_selector_all("iframe")
                    for i, f in enumerate(iframes):
                        src = await f.get_attribute("src")
                        self._log_execution(f"DEBUG: Found alternative iframe[{i}] src: {src}")

                    await self.capture_failure_artifact(f"nav_fail_attempt_{attempt}")

            except Exception as e:
                self._log_execution(f"DEBUG: Navigation error: {e}")
                await asyncio.sleep(2)

        return False

    async def _handle_regional_splash(self):
        """V5.13.1: Refactored Splash Bypass to avoid invalid selectors."""
        for attempt in range(2):
            try:
                # Use get_by_text for cleaner discovery
                el = self.page.get_by_text("Nigeria").last
                if await el.is_visible():
                    self._log_execution("DEBUG: Regional Splash detected (Nigeria). Clicking...")
                    await el.click(timeout=5000, force=True)
                    await asyncio.sleep(2) # Wait for modal to vanish
                    self._log_execution("DEBUG: Selected Region via text")
                    break
            except: pass

    async def _break_iframe_login(self):
        """V5.17.0: Manually injects accessToken into the Iframe LocalStorage."""
        try:
            token = self.auth_state.get("accessToken")
            if token:
                # V5.17.0 Force Iframe Injection
                await self.page.evaluate(f"""() => {{
                    document.querySelectorAll('iframe').forEach(f => {{
                        try {{
                            f.contentWindow.localStorage.setItem('patron:id:accesstoken', '{token}');
                            f.contentWindow.location.reload();
                        }} catch(e) {{}}
                    }});
                }}""")
                self._log_execution("DEBUG: Iframe Login Breaker: Token injected into iframe.")
                await asyncio.sleep(3)
        except Exception as e:
            self._log_execution(f"DEBUG: Iframe breaker failed: {e}")

    async def _handle_overlays(self, retries: int = 5):
        """V5.17.0: Ghost Bypass & Force-Close Protocol."""
        # V5.17.0 Ghost Bypass Click
        try:
            # Click at (10, 10) to clear transparent overlays as requested
            await self.page.mouse.click(10, 10)
            # Tutorial tooltips
            tooltip_close = self.page.locator(".m-tool-tips-close").first
            if await tooltip_close.is_visible():
                await tooltip_close.click(timeout=2000, force=True)
        except: pass

        # Forcefully hide common blockers via CSS Injection
        try:
            await self.page.add_style_tag(content="""
                .m-join-now, .join-now-banner, .m-app-banner, .m-join-header,
                .af-download-banner, .m-download-guide, .m-home-popup {
                    display: none !important;
                    visibility: hidden !important;
                    pointer-events: none !important;
                }
            """)
        except: pass

        selectors = [
            ".m-icon-close",
            "button.close-icon",
            ".modal-close",
            ".close-btn",
            ".m-app-banner .m-close-btn",
            ".m-close",
            ".af-download-banner .m-icon-close",
            ".m-tool-tips-close"
        ]

        for sel in selectors:
            for attempt in range(retries):
                try:
                    btn = self.page.locator(sel).first
                    if await btn.is_visible():
                        self._log_execution(f"DEBUG: Overlay ({sel}) detected. Closing (Attempt {attempt+1})...")
                        await btn.click(timeout=3000, force=True)
                        await asyncio.sleep(1)
                    else:
                        break
                except:
                    await asyncio.sleep(1)

    async def _log_request(self, request: Request):
        """V5.10.0: Enhanced endpoint capturing."""
        try:
            url = request.url.lower()
            if any(x in url for x in ["game", "spin", "bet", "api", "history", "result"]):
                entry = {"type": "REQUEST", "url": request.url, "method": request.method, "timestamp": time.time()}
                self.network_log.append(entry)

                # Discovery logic
                if "history" in url or "results" in url:
                    self._log_execution(f"DEBUG: Found History Endpoint -> {request.url}")
                    self.discovered_endpoints["history"] = request.url
                elif "bet" in url or "place" in url:
                    self._log_execution(f"DEBUG: Found Bet Endpoint -> {request.url}")
                    self.discovered_endpoints["bet"] = request.url
        except: pass

    async def _log_response(self, response: Response):
        try:
            url = response.url.lower()

            # V5.17.0 Recursive Refresh Loop (Interceptor)
            if any(x in url for x in ["/api/ng/orders/", "/api/ng/factscenter/", "config/refresh"]):
                try:
                    data = await response.json()
                    new_token = data.get("accessToken") or data.get("data", {}).get("accessToken")
                    if new_token:
                        self._log_execution(f"DEBUG: V5.17 Captured updated accessToken.")
                        self.auth_state["accessToken"] = new_token
                except: pass

            # Cloudflare Cookie Update
            cookies = await self.context.cookies()
            for c in cookies:
                if c["name"] == "__cf_bm":
                    self.auth_state["cf_bm"] = c["value"]

            if any(x in url for x in ["game", "spin", "bet", "api", "history", "result"]):
                body = None
                try:
                    raw = await response.body()
                    body = raw.decode("utf-8", errors="ignore")
                except: pass
                entry = {"type": "RESPONSE", "url": response.url, "response": body, "timestamp": time.time()}
                self.network_log.append(entry)
        except: pass

    def save_cycle_logs(self, confidence: float, spins: int):
        try:
            os.makedirs("artifacts", exist_ok=True)
            log_path = "artifacts/cycle_logs.txt"
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(f"=== OMNI MACHINE V3.0 ACCURACY AUDIT ===\n")
                f.write(f"STATE UPDATED: {spins} spins recorded. Confidence: {confidence*100:.1f}%\n")
                f.write("-" * 30 + "\n\n")
                f.write("--- EXECUTION STEPS ---\n")
                for step in self.execution_log: f.write(f"{step}\n")
        except: pass

    async def capture_history_texts(self) -> Dict[str, Any]:
        """V5.12.1: Dual-Method History Extraction (UI + Network)."""
        data = {"timestamp": time.time(), "results": []}

        # Method A: UI Scrape
        try:
            if self.game_frame:
                selectors = [".history-list", ".recent-results", ".history-item", ".result-item", ".history_ball"]
                items = []
                for sel in selectors:
                    try:
                        loc = self.game_frame.locator(sel)
                        # Extract up to 20 results as requested
                        found = await loc.all_inner_texts()
                        if found:
                            items = found[:20]
                            break
                    except: continue

                for text in items:
                    t = text.strip().upper()
                    if "UP" in t or "U" in t: data["results"].append("U")
                    elif "DOWN" in t or "D" in t: data["results"].append("D")
                    elif "MIDDLE" in t or "M" in t: data["results"].append("M")

                # Ensure chronological order (UI is usually reversed)
                data["results"] = data["results"][::-1]
        except Exception as e:
            self._log_execution(f"DEBUG: Scraper Error: {e}")

        # Method B: Network Interception (Merge findings)
        try:
            for entry in self.network_log:
                if entry["type"] == "RESPONSE" and any(x in entry["url"].lower() for x in ["spin", "history", "result"]):
                    try:
                        body = json.loads(entry["response"])
                        # Generic extractor for history lists in JSON
                        items = body if isinstance(body, list) else body.get("results", body.get("data", []))
                        for item in items:
                            val = str(item.get("outcome", item.get("val", item))).upper()[0]
                            if val in ["U", "D", "M"] and val not in data["results"][:5]:
                                # Only add if not recently scraped to avoid duplicates
                                data["results"].append(val)
                    except: pass
        except: pass

        self._log_execution(f"HISTORY EXTRACTED: {len(data['results'])} outcomes found.")
        return data

    async def place_ui_bet(self, direction: str, amount: float):
        try:
            if not self.game_frame: return False
            stake_input = self.game_frame.locator('input[type="number"]').first
            await stake_input.fill(str(amount))
            target_text = "UP" if direction == "U" else "DOWN"
            target = self.game_frame.locator("button", has_text=target_text).first
            await target.hover()
            await target.click(force=True)
            await asyncio.sleep(random.uniform(2.5, 6.8))
            return True
        except: return False

    async def get_full_session_state(self):
        """V5.15.0: Captures cookies, localStorage, and V5.15 auth_state."""
        cookies = await self.context.cookies()
        storage = await self.page.evaluate("""() => {
            return {
                local: { ...localStorage },
                session: { ...sessionStorage }
            };
        }""")

        # Sync current LocalStorage back to auth_state if possible
        ls = storage.get("local", {})
        self.auth_state["accessToken"] = ls.get("patron:id:accesstoken", self.auth_state["accessToken"])
        self.auth_state["refreshToken"] = ls.get("patron:id:refreshtoken", self.auth_state["refreshToken"])

        return {
            "cookies": cookies,
            "storage": storage,
            "auth_state": self.auth_state
        }

    async def get_session_cookies(self):
        return await self.context.cookies()

    async def close(self):
        try:
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except: pass
