import asyncio
import os
import json
from playwright.async_api import async_playwright
from pymongo import MongoClient
from datetime import datetime

async def run_login_flow():
    # Retrieve Secrets
    login_phone = os.environ.get("FOOTBALL_NG_LOGIN")
    login_pass = os.environ.get("FOOTBALL_NG_PASS")
    mongo_uri = os.environ.get("MONGODB_URI")

    if not all([login_phone, login_pass, mongo_uri]):
        print("Error: Missing required environment variables (FOOTBALL_NG_LOGIN, FOOTBALL_NG_PASS, MONGODB_URI).")
        return

    # Ensure artifacts directory exists
    os.makedirs("artifacts", exist_ok=True)

    async with async_playwright() as p:
        # Launch browser with stealth-like settings
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 375, 'height': 812},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/04.1"
        )
        page = await context.new_page()

        print("Navigating to login page...")
        # Common mobile login path
        await page.goto("https://www.football.com/ng/m/login", wait_until="networkidle")

        # Fill login details
        print("Filling login credentials...")
        try:
            # Targeting common patterns for mobile/password fields
            await page.wait_for_selector('input[type="tel"]', timeout=10000)
            await page.fill('input[type="tel"]', login_phone)
            await page.fill('input[type="password"]', login_pass)

            print("Submitting login...")
            # Often the button text contains 'Login' or it's a submit type
            await page.click('button:has-text("Login"), button[type="submit"]')
        except Exception as e:
            print(f"Selector error: {e}")
            await page.screenshot(path="artifacts/login_error.png")
            await browser.close()
            return

        # Wait for navigation/successful login indicator
        print("Waiting 10 seconds for login to complete and hydration...")
        await asyncio.sleep(10)

        # Verification Screenshot
        print("Capturing verification screenshot...")
        await page.screenshot(path="artifacts/login_verification.png", full_page=True)

        # Persist Session
        print("Capturing storage state...")
        storage = await context.storage_state()

        print("Persisting session to MongoDB...")
        try:
            client = MongoClient(mongo_uri)
            # Use 'football_bot' as default db if not specified in URI
            db = client.get_database("football_bot")

            db.titan_auth.update_one(
                {"type": "session_state"},
                {
                    "$set": {
                        "state": storage,
                        "updated_at": datetime.utcnow()
                    }
                },
                upsert=True
            )
            client.close()
            print("Session successfully persisted to titan_auth collection.")
        except Exception as e:
            print(f"MongoDB error: {e}")

        print("Login flow complete.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_login_flow())
