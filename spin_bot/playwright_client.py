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
from typing import List, Optional, Dict, Union
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

    def _log_execution(self, message: str):
        print(message)
        self.execution_log.append(f"[{time.ctime()}] {message}")

    async def setup(self, cookies: List[Dict] = None):
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

        if cookies:
            await self.context.add_cookies(cookies)
            self._log_execution("DEBUG: Persistent session cookies injected.")

        self.page = await self.context.new_page()
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
        self._log_execution(f"DEBUG: Initializing Aggressive Login sequence...")
        try:
            # V5.9.9: Clear everything and start at the independent login URL
            login_url = "https://www.football.com/ng/m/independent_login"
            await self.page.goto(login_url, wait_until="commit")
            await self._handle_regional_splash()

            # V5.9.5: Force navigation after splash as requested
            await self.page.goto("https://www.football.com", wait_until="networkidle")
            await self._handle_overlays()

            login_triggers = ["a[href*='login']", ".m-login-btn", "text=Login", "text=More"]
            for trigger in login_triggers:
                try:
                    el = self.page.locator(trigger).first
                    if await el.is_visible():
                        await el.click(timeout=5000)
                        await asyncio.sleep(2)
                        break
                except: pass

            try:
                btn = self.page.locator("text=Login / Register").first
                if await btn.is_visible(): await btn.click()
            except: pass

            await self.page.locator("input[placeholder*='Mobile']").first.fill(user)
            await self.page.locator("input[type='password']").first.fill(pw)

            # V5.9.6: Robust Lime-Green Login Button Logic
            login_btn = self.page.locator("text='Login'").filter(has_text="Login").first
            try:
                if await login_btn.is_visible():
                    self._log_execution("DEBUG: Green Login button detected. Clicking...")
                    await login_btn.click(force=True)
                else:
                    # Fallback selectors
                    fallback_selectors = [".m-btn-login", "div:has-text('Login')", "button[type='submit']", ".m-login-button"]
                    for sel in fallback_selectors:
                        el = self.page.locator(sel).first
                        if await el.is_visible():
                            self._log_execution(f"DEBUG: Fallback Login button detected ({sel}). Clicking...")
                            await el.click(force=True)
                            break
            except: pass

            # Post-Login Verification (V5.9.7: URL-based check)
            await asyncio.sleep(5)
            # Handle Post-Login Popups (Aggressive Click)
            try:
                popup_triggers = ["button:has-text('OK')", ".m-btn-confirm", ".close-icon", "text=Confirm"]
                for pt in popup_triggers:
                    el = self.page.locator(pt).first
                    if await el.is_visible():
                        await el.click(timeout=5000)
                        self._log_execution(f"DEBUG: Post-login popup ({pt}) cleared.")
            except: pass

            # V5.9.8: Robust Auth Verification
            try:
                auth_selectors = [".m-user-info", ".m-icon-user", "a[href*='me']", "text=Logout"]
                auth_verified = False
                for sel in auth_selectors:
                    try:
                        await self.page.wait_for_selector(sel, state="visible", timeout=15000)
                        self._log_execution(f"DEBUG: Login confirmed via {sel}")
                        auth_verified = True
                        break
                    except: pass

                if not auth_verified:
                    raise Exception("Auth verification timed out after login attempt.")

            except Exception as e:
                self._log_execution(f"WARNING: Login Verification Failed: {e}")
                await self.page.screenshot(path="artifacts/error.png")
                if retry:
                    self._log_execution("DEBUG: Attempting login retry...")
                    await self.login(retry=False)
                    return

            await asyncio.sleep(2)
            await self._handle_overlays()
        except Exception as e:
            self._log_execution(f"CRITICAL: Login UI Error: {e}")
            await self.page.screenshot(path="artifacts/error.png")

    async def navigate_to_game(self) -> bool:
        """V5.9.4: Anti-Redirect & Deep-Link Recovery."""
        target_url = os.getenv("SPIN_URL", "https://www.football.com/ng/games/spin")
        max_redirect_retries = 3

        for attempt in range(max_redirect_retries + 1):
            try:
                self._log_execution(f"DEBUG: Navigating to SPIN_URL (Attempt {attempt+1})...")
                await self.page.goto(target_url, wait_until="networkidle")

                # Check for Livescore Trap
                current_url = self.page.url
                if "livescore" in current_url.lower():
                    self._log_execution(f"WARNING: Redirected to {current_url}. Retrying target...")
                    if attempt < max_redirect_retries: continue
                    else: return False

                await self._handle_overlays()

                # V5.9.4 Deep-Link Iframe Wait
                self._log_execution("DEBUG: Searching for Game Iframe...")
                try:
                    await self.page.wait_for_selector("iframe", state="visible", timeout=5000)
                except:
                    # Search for Refresh/Reload button if iframe missing
                    self._log_execution("DEBUG: Iframe missing. Searching for Refresh/Reload triggers...")
                    refresh_btn = self.page.locator("text=Refresh, text=Reload, .refresh-btn").first
                    if await refresh_btn.is_visible():
                        await refresh_btn.click()
                        await asyncio.sleep(5)

                # Target specific sportygames frame
                try:
                    await self.page.wait_for_selector("iframe[src*='sportygames']", state="visible", timeout=15000)
                    self.game_frame = self.page.frame_locator("iframe[src*='sportygames']")
                    await self.game_frame.locator(".history_ball").first.wait_for(timeout=20000)
                    self._log_execution("DEBUG: Successfully attached to SportyGames environment.")
                    return True
                except:
                    # V5.9.8: Explicit Lobby Icon Interaction
                    self._log_execution("DEBUG: Scanning lobby for 'Spin Da Bottle' interaction icon...")
                    game_icons = [
                        "div.game-item:has-text('Spin Da Bottle')",
                        ".m-game-item:has-text('Spin Da Bottle')",
                        "text='Spin Da Bottle'",
                        ".game-item:has-text('Spin')"
                    ]
                    for icon_sel in game_icons:
                        try:
                            icon = self.page.locator(icon_sel).first
                            if await icon.is_visible():
                                self._log_execution(f"DEBUG: Target Game icon detected ({icon_sel}). Clicking...")
                                await icon.click(force=True)
                                await asyncio.sleep(5)

                                # Wait for transition to iframe (Max 30s as requested)
                                try:
                                    await self.page.wait_for_selector("iframe[src*='sportygames']", state="visible", timeout=30000)
                                    self.game_frame = self.page.frame_locator("iframe[src*='sportygames']")
                                    await self.game_frame.locator(".history_ball").first.wait_for(timeout=20000)
                                    self._log_execution("DEBUG: Successfully attached via Lobby Interaction.")
                                    return True
                                except: pass
                        except: pass
                    self._log_execution("CRITICAL: Lobby interaction failed to trigger iframe.")

            except Exception as e:
                self._log_execution(f"DEBUG: Navigation attempt failed: {e}")

        return False

    async def _handle_regional_splash(self):
        """V5.9.5: Aggressive Location/Country Selector Bypass."""
        selectors = [
            "div:has-text('Nigeria')",
            ".m-country-item:has-text('Nigeria')",
            "text=Nigeria",
            "text=Confirm",
            "button:has-text('Nigeria')",
            ".region-confirm"
        ]
        for sel in selectors:
            try:
                el = self.page.locator(sel).last
                if await el.is_visible():
                    self._log_execution(f"DEBUG: Regional Splash detected ({sel}). Clicking...")
                    await el.click(timeout=5000, force=True)
                    await asyncio.sleep(2) # Wait for modal to vanish
                    self._log_execution(f"DEBUG: Selected Region via {sel}")
                    break
            except: pass

    async def _handle_overlays(self):
        """V5.9.9: Kill Ad Banners with a 3-attempt limit and JS hiding fallback."""
        selectors = [
            "button.close-icon",
            ".modal-close",
            "[aria-label='Close']",
            ".close-btn",
            ".m-app-banner .m-close-btn",
            "text=Join Now",
            ".m-btn-join",
            ".m-close",
            "i.m-icon-close"
        ]

        # Stop sticky headers using JS as requested
        try:
            await self.page.evaluate("() => { document.querySelectorAll('.m-join-now, .join-now-banner, .m-app-banner').forEach(el => el.style.display = 'none'); }")
        except: pass

        for sel in selectors:
            attempts = 0
            try:
                while attempts < 3:
                    btn = self.page.locator(sel).first
                    if await btn.is_visible():
                        attempts += 1
                        self._log_execution(f"DEBUG: Overlay/Banner detected ({sel}). Closing attempt {attempts}...")
                        await btn.click(timeout=2000, force=True)
                        await asyncio.sleep(1)
                    else: break
            except: pass

    async def _log_request(self, request: Request):
        try:
            url = request.url.lower()
            if any(x in url for x in ["game", "spin", "bet", "api", "history"]):
                entry = {"type": "REQUEST", "url": request.url, "method": request.method, "timestamp": time.time()}
                self.network_log.append(entry)
        except: pass

    async def _log_response(self, response: Response):
        try:
            url = response.url.lower()
            if any(x in url for x in ["game", "spin", "bet", "api", "history"]):
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

    async def capture_history_texts(self) -> List[str]:
        try:
            if not self.game_frame: return []
            items = await self.game_frame.locator(".history_ball").all_inner_texts()
            outcomes = []
            for text in items:
                t = text.strip().upper()
                if "UP" in t or "U" in t: outcomes.append("U")
                elif "DOWN" in t or "D" in t: outcomes.append("D")
                else: outcomes.append("M")
            return outcomes[::-1]
        except: pass
        return []

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

    async def get_session_cookies(self):
        return await self.context.cookies()

    async def close(self):
        try:
            if self.browser: await self.browser.close()
            if self.playwright: await self.playwright.stop()
        except: pass
