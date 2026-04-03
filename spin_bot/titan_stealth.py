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

        # Titan-Stealth Emulation Specs
        self.context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Mobile Safari/537.36",
            viewport={'width': 390, 'height': 844},
            is_mobile=True,
            has_touch=True,
            locale="en-NG",
            timezone_id="Africa/Lagos",
            geolocation={"latitude": 6.5244, "longitude": 3.3792}, # Lagos, Nigeria
            permissions=["geolocation"],
            storage_state=storage_state
        )

        self.page = await self.context.new_page()
        if stealth:
            try:
                await stealth(self.page)
            except: pass
        self.page.set_default_timeout(15000)

    async def handle_region_trap(self):
        """V5.27.1: Region Trap - Select Nigeria to set session context."""
        try:
            modal = self.page.locator("[data-cms-key='location_preference']").first
            if await modal.is_visible():
                print("DEBUG: Region Trap detected. Selecting Nigeria...")
                # Must select country, not just close
                nigeria_item = self.page.locator(".m-list-item").filter(has_text="Nigeria").first
                await nigeria_item.wait_for(state="visible", timeout=5000)
                await nigeria_item.click(force=True)
                await asyncio.sleep(2)
        except Exception as e:
            print(f"DEBUG: Region trap check skipped/failed: {e}")

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

    async def login(self) -> bool:
        print("DEBUG: Starting Project Titan-Stealth login flow...")
        await self.setup_db()

        state = self.load_storage_state()
        await self.setup_browser(storage_state=state)

        try:
            # Step 1: Navigate
            await self.page.goto(self.login_url, wait_until="networkidle")

            # Step 2: Handle Region Trap
            await self.handle_region_trap()

            # Step 3: Check if already logged in via state
            if "/me" in self.page.url or await self.page.locator(".m-balance").is_visible():
                print("DEBUG: Session valid. Skipping login.")
                return True

            # Step 4: Perform login if not authenticated
            print("DEBUG: Session invalid or not found. Performing fresh login...")

            if not self.phone or not self.password:
                print("CRITICAL: Missing credentials (FOOTBALL_NG_LOGIN/PASS).")
                return False

            # Wait for inputs
            phone_sel = "input[type='tel'], input[placeholder*='Phone'], .un-input-wrapper input"
            await self.page.wait_for_selector(phone_sel, state="visible", timeout=15000)

            await self.human_type(phone_sel, self.phone)

            pass_sel = "input[type='password']"
            await self.human_type(pass_sel, self.password)

            login_btn = self.page.locator("button.login-btn, button.btn-primary:has-text('Login')").first
            await login_btn.click()

            # Step 5: Verify
            try:
                await self.page.wait_for_url("**/me", timeout=15000)
                print("DEBUG: Titan-Stealth Login Success.")

                # Step 6: Save state
                new_state = await self.context.storage_state()
                self.save_storage_state(new_state)
                return True
            except:
                print("CRITICAL: Redirect to /me failed.")
                await self.capture_failure("login_redirect_fail")
                return False

        except Exception as e:
            print(f"CRITICAL: Titan-Stealth Flow failed: {e}")
            await self.capture_failure("titan_flow_crash")
            return False

    async def close(self):
        if self.context: await self.context.close()
        if self.browser: await self.browser.close()
        if self.playwright: await self.playwright.stop()
        if self.db_client: self.db_client.close()
