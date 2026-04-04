import os
import asyncio
import json
import time
import random
from playwright.async_api import async_playwright, Page, BrowserContext
try:
    from playwright_stealth import stealth_async as stealth
except ImportError:
    try:
        from playwright_stealth import stealth
    except ImportError:
        stealth = None
from pymongo import MongoClient
from typing import Optional, Dict, Any

class TitanStealthClient:
    def __init__(self):
        self.login_url = "https://www.football.com/ng/m/independent_login"
        self.api_login_url = "https://www.football.com/api/ng/auth/login"
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

    async def setup_db(self):
        if not self.mongodb_uri:
            print("WARNING: MONGODB_URI not set. Session persistence disabled.")
            return
        try:
            self.db_client = MongoClient(self.mongodb_uri)
            self.db = self.db_client.get_database("spin_bot")
            self.collection = self.db.get_collection("sessions")
            print("DEBUG: MongoDB connection established.")
        except Exception as e:
            print(f"ERROR: MongoDB setup failed: {e}")

    def load_storage_state(self) -> Optional[Dict[str, Any]]:
        if self.collection is None: return None
        try:
            doc = self.collection.find_one({"id": "titan_stealth_session"})
            if doc and "storage_state" in doc:
                print("DEBUG: Loaded storage_state from MongoDB.")
                return doc["storage_state"]
        except Exception as e:
            print(f"DEBUG: Failed to load storage_state: {e}")
        return None

    def save_storage_state(self, state: Dict[str, Any]):
        if self.collection is None: return
        try:
            self.collection.update_one(
                {"id": "titan_stealth_session"},
                {"$set": {"storage_state": state, "updated_at": time.time()}},
                upsert=True
            )
            print("DEBUG: Saved storage_state to MongoDB.")
        except Exception as e:
            print(f"ERROR: Failed to save storage_state: {e}")

    async def setup_browser(self, storage_state: Optional[Dict[str, Any]] = None):
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(headless=True)

        # V5.27.4: Oppo A3x Fingerprint Protocol
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 14; CPH2641) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.6261.119 Mobile Safari/537.36",
            viewport={'width': 360, 'height': 800},
            is_mobile=True,
            has_touch=True,
            locale="en-NG",
            timezone_id="Africa/Lagos",
            geolocation={"latitude": 6.5244, "longitude": 3.3792},
            permissions=["geolocation"],
            storage_state=storage_state
        )

        # Pre-empt the Location Modal by injecting the region cookie
        await self.context.add_cookies([{
            "name": "region",
            "value": "NG",
            "domain": "www.football.com",
            "path": "/",
            "expires": time.time() + 31536000 # 1 year
        }])
        print("DEBUG: Pre-emptive Region Cookie Injected.")

        self.page = await self.context.new_page()
        if stealth:
            try:
                await stealth(self.page)
            except: pass
        self.page.set_default_timeout(15000)

    async def handle_region_trap(self):
        """V5.27.3: Vue.js State Sync - Handled pre-emptively via cookies in V5.27.4."""
        try:
            close_btn = self.page.locator('i.m-icon-close[data-op="region-close"]')
            if await close_btn.is_visible():
                await close_btn.click()
                print("DEBUG: Closed region modal via native click.")
                await asyncio.sleep(2)
        except: pass

    async def capture_failure(self, name: str):
        try:
            os.makedirs("artifacts", exist_ok=True)
            await self.page.screenshot(path=f"artifacts/{name}.png")
            content = await self.page.content()
            with open(f"artifacts/{name}.html", "w", encoding="utf-8") as f:
                f.write(content)
            print(f"DEBUG: Captured failure artifacts for {name}")
        except: pass

    async def human_type(self, selector: str, text: str):
        try:
            await self.page.locator(selector).first.click()
            for char in text:
                await self.page.keyboard.type(char)
                await asyncio.sleep(random.uniform(0.05, 0.15))
        except Exception as e:
            print(f"ERROR during human typing: {e}")
            raise e

    async def api_login_fallback(self) -> bool:
        """V5.27.4: Raw POST login fallback to bypass UI rendering issues."""
        print("DEBUG: Executing API-First login fallback...")
        try:
            payload = {
                "mobile": self.phone,
                "password": self.password,
                "remember": True
            }
            # Use the context's request for automatic cookie management
            response = await self.context.request.post(
                self.api_login_url,
                data=payload,
                headers={"Referer": self.login_url}
            )

            if response.status == 200:
                print("DEBUG: API Login Successful. Committing state...")
                new_state = await self.context.storage_state()
                self.save_storage_state(new_state)
                return True
            else:
                print(f"DEBUG: API Login failed with status {response.status}")
                return False
        except Exception as e:
            print(f"DEBUG: API fallback crash: {e}")
            return False

    async def login(self) -> bool:
        print("DEBUG: Starting Project Titan-Stealth login flow (OPPO FINGERPRINT PROTOCOL)...")
        await self.setup_db()

        state = self.load_storage_state()
        await self.setup_browser(storage_state=state)

        try:
            # Step 1: Navigate
            await self.page.goto(self.login_url, wait_until="networkidle")

            # Step 2: Modal Handling
            await self.handle_region_trap()

            # Step 3: Check Login Status
            if "/me" in self.page.url or await self.page.locator(".m-balance").is_visible():
                print("DEBUG: Session valid. Skipping login.")
                return True

            # Step 4: Perform UI Login
            print("DEBUG: Session invalid. Performing fresh UI login...")
            phone_sel = "input[type='tel']"

            try:
                # Attempt to find inputs
                await self.page.wait_for_selector(phone_sel, state="visible", timeout=5000)
            except:
                # Pro-Tip: Trigger scroll to force Vue hydration
                print("DEBUG: Primary inputs not visible. Triggering scroll event...")
                await self.page.mouse.wheel(0, 500)
                await asyncio.sleep(2)

                try:
                    await self.page.wait_for_selector(phone_sel, state="visible", timeout=5000)
                except:
                    # Final UI failure -> API Fallback
                    print("WARNING: UI login fields not found. Falling back to API login.")
                    return await self.api_login_fallback()

            await self.human_type(phone_sel, self.phone)
            await self.human_type("input[type='password']", self.password)

            login_btn = self.page.locator("button.login-btn, button.btn-primary:has-text('Login')").first
            await login_btn.click()

            # Step 5: Verify
            try:
                await self.page.wait_for_url("**/me", timeout=15000)
                print("DEBUG: Titan-Stealth Login Success.")
                new_state = await self.context.storage_state()
                self.save_storage_state(new_state)
                return True
            except:
                print("CRITICAL: Redirect to /me failed. Retrying via API fallback.")
                return await self.api_login_fallback()

        except Exception as e:
            print(f"CRITICAL: Titan-Stealth UI Flow failed: {e}. Attempting API fallback.")
            return await self.api_login_fallback()

    async def close(self):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()
        if self.db_client: self.db_client.close()
