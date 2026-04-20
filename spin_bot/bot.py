import os
import asyncio
import random
from playwright.async_api import async_playwright
from pymongo import MongoClient
from datetime import datetime, timezone
# Import game engine functionality
from spin_bot.game_engine import navigate_to_games_and_scrape

# Environment Secrets
DB_URI = os.getenv("MONGODB_URI")
USER_ID = os.getenv("FOOTBALL_NG_LOGIN")
PASSWORD = os.getenv("FOOTBALL_NG_PASS")

async def run_login_and_games():
    if not all([USER_ID, PASSWORD, DB_URI]):
        print("Error: Missing required environment variables.")
        return

    # Ensure artifacts directory exists
    os.makedirs("artifacts", exist_ok=True)

    async with async_playwright() as p:
        # 1. INITIALIZE CONTEXT (iPhone 13 emulation)
        device = p.devices['iPhone 13']
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(**device)
        page = await context.new_page()

        print("DEBUG: Navigating to Mobile Home Root...")
        await page.goto("https://www.football.com/ng/m/", wait_until="networkidle")

        # 2. LIGHTWEIGHT LOCATION PREFERENCE HANDLER (Nigeria selection)
        try:
            # Check once for the Location Preference modal
            location_modal = page.locator(".dialog-wrapper, .m-dialog").first
            if await location_modal.is_visible(timeout=5000):
                print("DEBUG: Location Preference modal detected. Selecting Nigeria...")
                # Click the Nigeria option explicitly
                nigeria_opt = page.locator("text=Nigeria").first
                if await nigeria_opt.is_visible():
                    await nigeria_opt.click(force=True)
                    print("DEBUG: Nigeria clicked. Waiting for UI to settle...")
                    await asyncio.sleep(3) # Human delay for UI to settle
        except Exception as e:
            print(f"DEBUG: Location preference check bypassed: {e}")

        # 3. CLEAN LOGIN FLOW (Reverted to last known working version)
        try:
            print("DEBUG: Attempting click on Home Screen Login button...")
            login_link = ".m-btn-login"
            await page.wait_for_selector(login_link, timeout=10000)
            await page.click(login_link, force=True)

            print("DEBUG: Waiting for phone/password form...")
            await page.wait_for_selector("input[type='tel']", timeout=10000)

            print("DEBUG: Entering credentials...")
            await page.fill("input[type='tel']", USER_ID)
            await page.fill("input[type='password']", PASSWORD)

            print("DEBUG: Clicking submit button...")
            # Using the confirmed submit button selector for the login form
            await page.click("button.login-btn, [data-op='login-btn']", force=True)

            print("DEBUG: Waiting for login processing...")
            await asyncio.sleep(10)

            # 4. VERIFY LOGIN SUCCESS
            if "/m/login" not in page.url:
                print(f"SUCCESS: Logged in! Current URL: {page.url}")
                storage = await context.storage_state()

                # PERSIST SESSION TO MONGODB
                if DB_URI:
                    try:
                        client = MongoClient(DB_URI)
                        db = client['broker_db']
                        db.titan_auth.update_one(
                            {"account": USER_ID},
                            {"$set": {"session_data": storage, "updated_at": datetime.now(timezone.utc)}},
                            upsert=True
                        )
                        client.close()
                        print("DEBUG: Session saved to MongoDB.")
                    except Exception as mongo_err:
                        print(f"DEBUG: MongoDB error: {mongo_err}")

                await page.screenshot(path="artifacts/login_success.png")

                # 5. INTEGRATE GAME ENGINE NAVIGATION
                # Human-like delay after successful login
                delay = random.uniform(2.5, 4.0)
                print(f"DEBUG: Human-like delay of {delay:.2f}s before navigation...")
                await asyncio.sleep(delay)

                print("DEBUG: Navigating to Games section...")
                # Call the modular game engine logic
                await navigate_to_games_and_scrape(page)

            else:
                print("CRITICAL: Stuck on login screen.")
                await page.screenshot(path="artifacts/login_failed_final.png")

        except Exception as e:
            print(f"ERROR during main flow: {e}")
            await page.screenshot(path="artifacts/fatal_error.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_login_and_games())
