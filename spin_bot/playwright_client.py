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

        self.context = await self.browser.new_context(
            **iphone_13,
            locale="en-NG",
            timezone_id="Africa/Lagos",
            ignore_https_errors=True
        )

        # V5.9.4 Anti-Redirect Header
        await self.context.set_extra_http_headers({"X-Requested-With": "com.android.browser"})

        # V5.13.2: Full Session Injection (Cookies + Storage)
        if cookies:
            try:
                await self.context.add_cookies(cookies)
                self._log_execution("DEBUG: API session cookies injected into Browser context.")
            except Exception as e:
                self._log_execution(f"DEBUG: Cookie injection failed: {e}")

        self.page = await self.context.new_page()

        if session_state and "storage" in session_state:
            try:
                storage = session_state["storage"]
                await self.page.add_init_script(f"""
                    if (window.location.hostname.includes('football.com')) {{
                        const local = {json.dumps(storage.get('local', {}))};
                        const session = {json.dumps(storage.get('session', {}))};
                        for (const k in local) localStorage.setItem(k, local[k]);
                        for (const k in session) sessionStorage.setItem(k, session[k]);
                    }}
                """)
                self._log_execution("DEBUG: Session storage injected into Browser context.")
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
        self._log_execution(f"DEBUG: Initializing SELF-SORTING LOGIN (V5.13.1)...")
        try:
            # 1. Direct Login Landing
            login_url = "https://www.football.com/ng/m/independent_login"
            await self.page.goto(login_url, wait_until="commit")
            await self._handle_regional_splash()
            await self._handle_overlays()

            # 2. Trigger Login UI (Click Top-Right Login Button)
            try:
                login_trigger = self.page.get_by_text("Log In", exact=True).first
                if await login_trigger.is_visible():
                    await login_trigger.click(force=True)
                    await asyncio.sleep(1)
            except: pass

            # 3. V5.13.1: Login Modal Verification
            modal_indicator = self.page.locator("input").first
            await modal_indicator.wait_for(state="visible", timeout=15000)

            # 4. Registration Bypass (if modal is registration-first)
            login_link = self.page.get_by_text("Log In").last
            if await login_link.is_visible():
                self._log_execution("DEBUG: Switching from registration to login...")
                await login_link.click(force=True)
                await asyncio.sleep(2)

            # 4. Input with Trusted Events (React/Vue Sync)
            self._log_execution("DEBUG: Entering credentials...")
            # Use get_by_placeholder as requested
            mobile_input = self.page.get_by_placeholder("Mobile Number").first
            if not await mobile_input.is_visible():
                mobile_input = self.page.locator("input[type='tel']").first

            pass_input = self.page.locator("input[type='password']").first

            # JS-based input injection to bypass visibility/attachment checks
            await self.page.evaluate("""([u, p]) => {
                const m = document.querySelector('input[type="tel"], input[placeholder*="Mobile"]');
                const pw = document.querySelector('input[type="password"]');
                if (m) {
                    m.value = u;
                    m.dispatchEvent(new Event('input', { bubbles: true }));
                    m.dispatchEvent(new Event('change', { bubbles: true }));
                }
                if (pw) {
                    pw.value = p;
                    pw.dispatchEvent(new Event('input', { bubbles: true }));
                    pw.dispatchEvent(new Event('change', { bubbles: true }));
                }
            }""", [user, pw])

            # 5. Submission
            # Refactored selector to avoid invalid patterns
            login_btn = self.page.locator("button.m-btn-login, .m-login-btn").first
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
        """V5.13.1: Robust Lobby-based Discovery & Iframe Sync."""
        target_url = os.getenv("SPIN_URL", "https://www.football.com/ng/games/spin")

        # 1. Clean Landing post-auth
        if "login" in self.page.url or "independent_login" in self.page.url:
            await self.page.goto("https://www.football.com/ng/", wait_until="networkidle")

        for attempt in range(3): # 3 retry loop as requested
            try:
                self._log_execution(f"DEBUG: Game Navigation Attempt {attempt+1}...")
                await self._handle_overlays()

                # 2. Navigate via 'Games' Icon in Bottom Nav (Robust Path)
                try:
                    games_nav = self.page.get_by_text("Games").last
                    if await games_nav.is_visible():
                        await games_nav.click(force=True)
                        await asyncio.sleep(2)
                except: pass

                # 3. Wait for Lobby Hydration (Increased timeout for high-latency environments)
                # Refactored wait_for_selector to avoid text=
                await self.page.wait_for_selector(".m-game-item, .game-item", state="visible", timeout=45000)

                # 4. Targeted Discovery: "Spin" via robust locator (V5.13.2 Nuclear Mode)
                self._log_execution("DEBUG: Searching for 'Spin' icon in lobby...")
                # Try image with alt text first as it's more robust than text-based filter on generic containers
                game_target = self.page.locator("img[alt*='Spin'], img[alt*='spin'], .m-game-item").filter(has_text="Spin").first

                if await game_target.is_visible():
                    await game_target.scroll_into_view_if_needed()
                    await asyncio.sleep(1)
                    await game_target.click(force=True)
                    self._log_execution("DEBUG: Game icon clicked. Syncing with iframe...")
                else:
                    # Fallback to direct URL if lobby icon is elusive
                    self._log_execution("DEBUG: Lobby icon elusive. Attempting direct SPIN_URL...")
                    await self.page.goto(target_url, wait_until="networkidle")

                # 4. Iframe Sync & UI Verification (Extended verification for game initialization)
                try:
                    self._log_execution("DEBUG: Waiting for Game Iframe (iframe[src*='sportygames'])...")
                    # V5.13.1: Specific frame locator as requested
                    self.game_frame = self.page.frame_locator("iframe[src*='sportygames']")

                    # Wait for Game UI: canvas, .history, .results as requested
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

    async def _handle_overlays(self, retries: int = 5):
        """V5.13.1: Robust Overlay Handling with CSS injection and JS clearing."""
        # 1. Clear Tutorial Tooltips (Mouse Click & Selector)
        try:
            await self.page.mouse.click(10, 10)
            tooltip_close = self.page.locator(".m-tool-tips-close").first
            if await tooltip_close.is_visible():
                await tooltip_close.click(timeout=2000)
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
        """V5.13.2: Captures cookies, localStorage, and sessionStorage."""
        cookies = await self.context.cookies()
        storage = await self.page.evaluate("""() => {
            return {
                local: { ...localStorage },
                session: { ...sessionStorage }
            };
        }""")
        return {"cookies": cookies, "storage": storage}

    async def get_session_cookies(self):
        return await self.context.cookies()

    async def close(self):
        try:
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except: pass
