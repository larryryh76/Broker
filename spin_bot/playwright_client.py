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

    async def setup(self, session_state: Dict = None):
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

        # V5.23.1 TECHNICAL ANALYSIS: iPhone X Viewport 375x812
        proxy_server = os.getenv("PROXY_SERVER")
        proxy_config = {"server": proxy_server} if proxy_server else None
        if proxy_config and os.getenv("PROXY_USERNAME"):
            proxy_config["username"] = os.getenv("PROXY_USERNAME")
            proxy_config["password"] = os.getenv("PROXY_PASSWORD")

        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/15.0 Mobile/15E148 Safari/604.1",
            viewport={'width': 375, 'height': 812},
            is_mobile=True,
            locale="en-NG",
            timezone_id="Africa/Lagos",
            ignore_https_errors=True,
            bypass_csp=True,
            proxy=proxy_config
        )

        # V5.20.1: Immortal Session Injection (Cookies + Storage)
        if session_state:
            try:
                if "cookies" in session_state:
                    await self.context.add_cookies(session_state["cookies"])

                if "storage" in session_state:
                    storage = session_state["storage"]
                    # Injection via init script to ensure consistency
                    await self.context.add_init_script(f"""
                        const local = {json.dumps(storage.get('local', {}))};
                        const session = {json.dumps(storage.get('session', {}))};
                        if (window.location.hostname.includes('football.com')) {{
                            for (const k in local) localStorage.setItem(k, local[k]);
                            for (const k in session) sessionStorage.setItem(k, session[k]);
                        }}
                    """)
                self._log_execution("DEBUG: Immortal Session Injected into Browser Context.")
            except Exception as e:
                self._log_execution(f"DEBUG: Session injection failed: {e}")

        self.page = await self.context.new_page()

        self._log_execution("DEBUG: V5.24.1 Aurora Protocol Active (Safari Stealth).")

        self.page.set_default_timeout(60000)
        self.page.on("request", self._log_request)
        self.page.on("response", self._log_response)

        # V5.21.1: UI Sensitivity & Modal Handling
        await self._apply_v21_ui_enhancements()

        if stealth:
            try: await stealth(self.page)
            except: pass
        await self.page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

    async def login(self, retry: bool = True):
        user = os.getenv("FOOTBALL_NG_LOGIN")
        pw = os.getenv("FOOTBALL_NG_PASS")
        if not user or not pw: return
        self._log_execution(f"DEBUG: Initializing V5.24.1 AURORA LOGIN (ANIMATION PATCH)...")
        try:
            # V5.23.1: Navigate to the specialized mobile login root
            login_url = "https://www.football.com/ng/m/independent_login"
            if login_url not in self.page.url:
                self._log_execution(f"DEBUG: Navigating to mobile login: {login_url}...")
                await self.page.goto(login_url, wait_until="networkidle")

            # V5.22.1: WAP OVERLAY CARPET BOMB: Attempt to open the mobile login drawer
            self._log_execution("DEBUG: Triggering WAP Login overlay...")
            wap_triggers = [
                "text='Log In'",
                "text='Login'",
                "button.login-btn",
                ".m-btn-login",
                ".icon-profile",
                "text='Me'",
                "a[href*='/login']"
            ]

            drawer_opened = False
            for selector in wap_triggers:
                try:
                    trigger = self.page.locator(selector).first
                    # Use wait_for(state='visible') to simulate timeout
                    await trigger.wait_for(state="visible", timeout=1500)
                    if await trigger.is_visible():
                        await trigger.click()
                        self._log_execution(f"DEBUG: WAP overlay opened via '{selector}'")
                        drawer_opened = True
                        break
                except:
                    continue

            if not drawer_opened:
                self._log_execution("WARNING: No WAP login trigger found. Form might already be open.")

            # V5.24.1: MECHANICAL DELAY for drawer animation
            self._log_execution("DEBUG: Waiting for drawer animation (1s)...")
            await asyncio.sleep(1)

            # V5.24.1: Robust Selector Search for Animated Drawer
            self._log_execution("DEBUG: Waiting for the login form to render...")

            # Prioritize Phone Number placeholder then input[type='tel'] then .un-input-wrapper input
            phone_input = None
            for sel in [
                "input[placeholder*='Phone Number']",
                "input[type='tel']",
                ".un-input-wrapper input",
                "input[placeholder*='Mobile']"
            ]:
                try:
                    loc = self.page.locator(sel).first
                    # Force wait until the element is actually ready to receive text
                    await loc.wait_for(state="visible", timeout=5000)
                    if await loc.is_visible():
                        phone_input = loc
                        break
                except: continue

            if not phone_input:
                self._log_execution("DEBUG: Drawer open but inputs hidden. Capturing failure artifact.")
                await self.capture_failure_artifact("drawer_inputs_hidden")
                raise Exception("Phone input not found after drawer open.")

            self._log_execution("DEBUG: Entering credentials...")
            await phone_input.click()
            await phone_input.fill(user)

            pass_input = self.page.locator("input[type='password']:visible").first
            await pass_input.fill(pw)

            # V5.24.1: Click the 'real' login button inside the drawer
            submit_btn = self.page.locator("button.login-btn:visible, .login-submit-btn:visible, button.btn-primary:visible, button[type='submit']:visible, .m-login-btn:visible").first
            await submit_btn.click()

            # STEP D: AURORA VERIFICATION
            try:
                self._log_execution("DEBUG: Verifying Titan Auth (30s)...")
                # Wait for redirect to /me or presence of balance
                await asyncio.wait_for(
                    asyncio.gather(
                        self.page.wait_for_url("**/me", timeout=30000),
                        self.page.wait_for_selector(".m-balance, button:has-text('Deposit')", state="visible", timeout=30000)
                    ),
                    timeout=35000
                )
                self._log_execution("TITAN LOGIN SUCCESS")
            except Exception as e:
                # V5.23.1 Check for Error Messages
                error_div = self.page.locator(".m-error, .error-msg, .m-tips").first
                if await error_div.is_visible():
                    msg = await error_div.text_content()
                    self._log_execution(f"CRITICAL: UI AUTH REJECTED: {msg}")
                else:
                    self._log_execution(f"CRITICAL: UI AUTH REJECTED: {e}")

                await self.capture_failure_artifact("titan_auth_rejected")
                import sys
                sys.exit(1)

            await asyncio.sleep(2)
            await self._handle_overlays()
        except Exception as e:
            self._log_execution(f"CRITICAL: V5.24.1 Login Error: {e}")
            await self.capture_failure_artifact("titan_login_error")
            import sys
            sys.exit(1)

    async def navigate_to_game(self) -> bool:
        """V5.24.1: Aurora Protocol - Hard-Nav Modal Breaker & WAP Redirect Handling."""
        target_url = "https://www.football.com/ng/games/spin-da-bottle"

        for attempt in range(3):
            try:
                self._log_execution(f"DEBUG: V5.24.1 Aurora Navigation Attempt {attempt+1}...")

                # STEP A: DIRECT NAVIGATION
                await self.page.goto(target_url, wait_until="networkidle")
                await self._apply_v21_ui_enhancements()
                await self._handle_overlays()

                # STEP B: HARD-NAV MODAL BREAKER (V5.22.1 WAP BYPASS)
                # Escape the game modal by forcing navigation to mobile root
                modal_detected = self.page.locator(".modal-content").first
                try:
                    await modal_detected.wait_for(state="visible", timeout=5000)
                    self._log_execution("DEBUG: Modal Trap detected. Forcing navigation to clear state...")

                    # V5.23.1: Navigate to the independent login directly if trapped
                    await self.page.goto("https://www.football.com/ng/m/independent_login", wait_until="networkidle")

                    # 2. Wait for redirects to fully settle
                    await asyncio.sleep(3)
                    self._log_execution(f"DEBUG: Settled on URL: {self.page.url}")

                    await self.login()
                except:
                    # No modal detected or already logged in
                    pass

                # V5.20.1: Iframe Sync
                self.game_frame = self.page.frame_locator("iframe[src*='sportygames']")

                # Verify if we are logged in
                try:
                    await self.page.wait_for_selector(".m-user-info, .m-balance", timeout=5000)
                    self._log_execution("DEBUG: Titan Session Authenticated.")
                except:
                    self._log_execution("WARNING: Session not visually verified.")

                # 4. Iframe Sync & UI Verification
                try:
                    self._log_execution("DEBUG: Waiting for Game Iframe Sync...")
                    ui_indicator = self.game_frame.locator("canvas, .history, .results, .history-list, .bet-panel").first
                    await ui_indicator.wait_for(state="visible", timeout=45000)

                    self._log_execution("IFRAME FOUND")
                    await self.hide_init_loader()
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

    async def _apply_v21_ui_enhancements(self):
        """V5.21.1: Implements UI Sensitivity, Modal Handling, and Asset Resilience."""
        try:
            self._log_execution("DEBUG: Applying V5.21.1 UI Enhancements...")
            await self.page.add_init_script("""
                (function() {
                    // 1. Asset Resilience: Preconnect/DNS-Prefetch
                    const domains = ['https://www.football.com', 'https://s.football.com/games/'];
                    domains.forEach(d => {
                        ['preconnect', 'dns-prefetch'].forEach(rel => {
                            const link = document.createElement('link');
                            link.rel = rel;
                            link.href = d;
                            document.head.appendChild(link);
                        });
                    });

                    // 2. Asset Retry Hook
                    window.addEventListener('error', function(e) {
                        const target = e.target;
                        if (target && (target.tagName === 'SCRIPT' || target.tagName === 'LINK')) {
                            const retryCount = parseInt(target.getAttribute('data-retry') || '0');
                            if (retryCount < 2) {
                                console.log(`DEBUG: Retrying asset load: ${target.src || target.href}`);
                                const newTarget = document.createElement(target.tagName);
                                if (target.tagName === 'SCRIPT') {
                                    newTarget.src = target.src;
                                    newTarget.async = true;
                                } else {
                                    newTarget.rel = 'stylesheet';
                                    newTarget.href = target.href;
                                }
                                newTarget.setAttribute('data-retry', retryCount + 1);
                                document.head.appendChild(newTarget);
                            } else {
                                console.error('FATAL ERROR: Asset failed to load after 2 retries.');
                            }
                        }
                    }, true);

                    // 3. Theme-Based Loading UI & Z-Index Management
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
                                if (brand === 'Encore') {
                                    loader.style.backgroundColor = '#100e26';
                                } else {
                                    loader.style.backgroundColor = '#000000';
                                }
                            }
                        }
                    }

                    // MutationObserver to handle dynamic elements and modal stack
                    const observer = new MutationObserver((mutations) => {
                        applyThemeStyle();

                        // Z-Index Management
                        const backdrops = document.querySelectorAll('.modal-backdrop');
                        const contents = document.querySelectorAll('.modal-content');

                        backdrops.forEach((b, i) => {
                            b.style.zIndex = (1052 + (i * 10)).toString();
                        });
                        contents.forEach((c, i) => {
                            c.style.zIndex = (1055 + (i * 10)).toString();
                        });
                    });
                    observer.observe(document.body, { childList: true, subtree: true });

                    // 4. "Login required" Listener
                    const originalFetch = window.fetch;
                    window.fetch = async (...args) => {
                        try {
                            const response = await originalFetch(...args);
                            if (response.status === 401) {
                                triggerLoginModal();
                            }
                            return response;
                        } catch (e) {
                            throw e;
                        }
                    };

                    function triggerLoginModal() {
                        if (document.getElementById('omni-login-modal')) return;

                        const modal = document.createElement('div');
                        modal.id = 'omni-login-modal';
                        modal.innerHTML = `
                            <div class="modal-backdrop" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);display:flex;align-items:center;justify-content:center;">
                                <div class="modal-content" style="background:white;padding:20px;border-radius:8px;text-align:center;max-width:80%;">
                                    <p style="color:red;font-weight:bold;">Error! Please login to start game.</p>
                                    <div style="margin-top:20px;">
                                        <button id="omni-login-primary" style="background:#007bff;color:white;border:none;padding:10px 20px;border-radius:4px;margin-right:10px;">Login</button>
                                        <button id="omni-login-secondary" style="background:#6c757d;color:white;border:none;padding:10px 20px;border-radius:4px;">Exit</button>
                                    </div>
                                </div>
                            </div>
                        `;
                        document.body.appendChild(modal);

                        document.getElementById('omni-login-primary').onclick = () => {
                            window.location.href = '/ng/login';
                        };
                        document.getElementById('omni-login-secondary').onclick = () => {
                            modal.remove();
                            window.location.href = '/ng/m/';
                        };
                    }

                    // Also check for specific text patterns in existing UI
                    setInterval(() => {
                        if (document.body.innerText.includes('Error! Please login to start game')) {
                            triggerLoginModal();
                        }
                    }, 2000);

                })();
            """)
        except Exception as e:
            self._log_execution(f"DEBUG: Failed to apply V5.21 enhancements: {e}")

    async def hide_init_loader(self):
        """V5.21.1: Hides the application initialization loader."""
        try:
            self._log_execution("DEBUG: Hiding App Init Loader...")
            await self.page.evaluate("""() => {
                const loader = document.querySelector('.app-init-loader-wrap');
                if (loader) loader.style.display = 'none';
            }""")
        except: pass

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
