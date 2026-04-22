import os
import asyncio
import random
from playwright.async_api import async_playwright
from pymongo import MongoClient
from datetime import datetime, timezone

# Import game engine
from spin_bot.game_engine import navigate_to_games_and_scrape, close_any_blocking_overlay

# Load secrets
DB_URI = os.getenv("MONGODB_URI")
USER_ID = os.getenv("FOOTBALL_NG_LOGIN")
PASSWORD = os.getenv("FOOTBALL_NG_PASS")

async def run_bot():
    if not all([USER_ID, PASSWORD, DB_URI]):
        print("❌ Missing required secrets (FOOTBALL_NG_LOGIN, FOOTBALL_NG_PASS, MONGODB_URI)")
        return

    os.makedirs("artifacts", exist_ok=True)

    async with async_playwright() as p:
        # Use iPhone 13 profile for best mobile rendering
        device = p.devices["iPhone 13"]
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(**device)
        page = await context.new_page()

        print("🌍 Navigating to https://www.football.com/ng/m/")
        await page.goto("https://www.football.com/ng/m/", wait_until="networkidle", timeout=60000)

        await asyncio.sleep(random.uniform(3, 5))

        # === ROBUST POPUP HANDLER ===
        print("🔍 Closing any initial popups...")
        await close_any_blocking_overlay(page)

        # === LOGIN FLOW ===
        print("🔑 Starting login...")
        try:
            # Click Login button
            await page.locator("button:has-text('Log'), .m-btn-login, text=Login").first.click(timeout=15000)
            await asyncio.sleep(random.uniform(2, 4))

            # Fill credentials
            await page.locator("input[type='tel'], input[placeholder*='phone' i]").fill(USER_ID)
            await page.locator("input[type='password']").fill(PASSWORD)

            # Submit
            await page.locator("button:has-text('Log In'), button:has-text('Login'), button[type='submit']").first.click()
            print("✅ Submitted login form")

            await asyncio.sleep(10)  # Wait for redirect

            if "/m/" in page.url and "login" not in page.url.lower():
                print(f"✅ SUCCESS: Logged in! Current URL: {page.url}")

                # Save session to MongoDB
                try:
                    client = MongoClient(DB_URI)
                    db = client["broker_db"]
                    storage = await context.storage_state()
                    db.titan_auth.update_one(
                        {"account": USER_ID},
                        {"$set": {
                            "session_data": storage,
                            "updated_at": datetime.now(timezone.utc),
                            "status": "active"
                        }},
                        upsert=True
                    )
                    client.close()
                    print("✅ Session saved to MongoDB")
                except Exception as e:
                    print(f"⚠️ MongoDB save failed: {e}")

                await page.screenshot(path="artifacts/1_login_success.png", full_page=True)

                # Go to Games
                await asyncio.sleep(random.uniform(2.5, 4))
                await navigate_to_games_and_scrape(page)

            else:
                print("❌ Login failed or stuck on login page")
                await page.screenshot(path="artifacts/login_failed.png", full_page=True)

        except Exception as e:
            print(f"❌ Error during login: {e}")
            await page.screenshot(path="artifacts/fatal_error.png", full_page=True)

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
