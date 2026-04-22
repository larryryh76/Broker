import os
import asyncio
import random
from playwright.async_api import async_playwright
from pymongo import MongoClient
from datetime import datetime, timezone

# Import game engine (only for games part)
from game_engine import navigate_to_games_and_scrape

# Secrets
DB_URI = os.getenv("MONGODB_URI")
USER_ID = os.getenv("FOOTBALL_NG_LOGIN")
PASSWORD = os.getenv("FOOTBALL_NG_PASS")

async def close_location_preference(page):
    """Specific handler for Location Preference modal"""
    print("🔍 Checking for Location Preference modal...")
    try:
        # Wait a bit for modal to appear
        await asyncio.sleep(3)
        
        nigeria_option = page.locator("text=Nigeria").first
        if await nigeria_option.is_visible(timeout=8000):
            await nigeria_option.click(force=True)
            print("✅ Selected Nigeria in location preference")
            await asyncio.sleep(random.uniform(2.5, 4))
            return True
    except:
        print("No location preference modal detected or already handled")
    return False

async def run_bot():
    if not all([USER_ID, PASSWORD, DB_URI]):
        print("❌ Missing secrets. Check GitHub Secrets.")
        return

    os.makedirs("artifacts", exist_ok=True)

    async with async_playwright() as p:
        device = p.devices["iPhone 13"]
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(**device)
        page = await context.new_page()

        print("🌍 Navigating to football.com...")
        await page.goto("https://www.football.com/ng/m/", wait_until="networkidle", timeout=60000)

        await asyncio.sleep(random.uniform(3, 5))

        # Handle Location Preference FIRST
        await close_location_preference(page)

        # === LOGIN FLOW ===
        print("🔑 Starting login...")
        try:
            # Click Login button
            await page.locator("button:has-text('Log'), button:has-text('Login'), .m-btn-login, [data-op='nav-login']").first.click(timeout=15000)
            await asyncio.sleep(random.uniform(2, 4))

            # Fill credentials
            await page.locator("input[type='tel'], input[placeholder*='phone' i]").fill(USER_ID)
            await page.locator("input[type='password']").fill(PASSWORD)
            print("✅ Filled login credentials")

            # Submit
            await page.locator("button:has-text('Log In'), button:has-text('Login'), button[type='submit']").first.click()
            print("✅ Submitted login")

            await asyncio.sleep(10)

            if "login" not in page.url.lower():
                print(f"✅ SUCCESS: Logged in! Current URL: {page.url}")

                # Save session to MongoDB
                try:
                    client = MongoClient(DB_URI)
                    db = client["broker_db"]
                    storage = await context.storage_state()
                    db.titan_auth.update_one(
                        {"account": USER_ID},
                        {"$set": {"session_data": storage, "updated_at": datetime.now(timezone.utc), "status": "active"}},
                        upsert=True
                    )
                    client.close()
                    print("✅ Session saved to MongoDB")
                except Exception as e:
                    print(f"⚠️ MongoDB save error: {e}")

                await page.screenshot(path="artifacts/1_login_success.png", full_page=True)

                # Navigate to Games using game_engine
                await asyncio.sleep(random.uniform(2.5, 4.5))
                await navigate_to_games_and_scrape(page)

            else:
                print("❌ Still on login page")
                await page.screenshot(path="artifacts/login_failed.png", full_page=True)

        except Exception as e:
            print(f"❌ Login error: {e}")
            await page.screenshot(path="artifacts/login_error.png", full_page=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
