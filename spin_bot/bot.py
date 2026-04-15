import os
import asyncio
from playwright.async_api import async_playwright
from pymongo import MongoClient
from datetime import datetime

# Environment Secrets
DB_URI = os.getenv("MONGODB_URI")
USER_ID = os.getenv("FOOTBALL_NG_LOGIN")
PASSWORD = os.getenv("FOOTBALL_NG_PASS")

async def run_login():
    if not all([USER_ID, PASSWORD, DB_URI]):
        print("Error: Missing required environment variables (FOOTBALL_NG_LOGIN, FOOTBALL_NG_PASS, MONGODB_URI).")
        return

    # Ensure artifacts directory exists
    os.makedirs("artifacts", exist_ok=True)

    async with async_playwright() as p:
        # Use iPhone 13 device profile
        device = p.devices['iPhone 13']
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(**device)
        page = await context.new_page()

        print("DEBUG: Navigating to Mobile Home Root...")
        await page.goto("https://www.football.com/ng/m/", wait_until="networkidle")

        # 1. HANDLE THE REGION SELECTOR POPUP
        try:
            print("DEBUG: Checking for the Ghana/Nigeria region popup...")
            # Wait a few seconds to see if the IP-mismatch popup triggers
            dialog = page.locator(".dialog-wrapper, .m-dialog")

            # Using a short timeout to check for the popup
            if await dialog.is_visible(timeout=6000):
                print("DEBUG: Region popup detected! Looking for 'Nigeria'...")
                # Instruct Playwright to find the word 'Nigeria' and click it
                await page.locator("text=Nigeria").first.click(force=True)
                print("DEBUG: Clicked 'Nigeria'. Waiting for UI to settle...")
                await asyncio.sleep(3) # Give the modal time to slide away
            else:
                print("DEBUG: No region popup detected.")
        except Exception as e:
            print(f"DEBUG: Region popup check finished or bypassed: {e}")

        # 2. CLICK THE ACTUAL LOGIN BUTTON
        try:
            print("DEBUG: Attempting forced click on the Home Screen Login button...")
            login_selector = ".m-btn-login"
            await page.wait_for_selector(login_selector, timeout=10000)
            await page.click(login_selector, force=True)

            # 3. FILL CREDENTIALS
            print("DEBUG: Waiting for the phone/password form to appear...")
            await page.wait_for_selector("input[type='tel']", timeout=10000)

            print("DEBUG: Form found. Entering credentials...")
            await page.fill("input[type='tel']", USER_ID)
            await page.fill("input[type='password']", PASSWORD)

            # Submit the form
            print("DEBUG: Clicking submit...")
            # targeting common submit button patterns on the login page
            await page.click("button.m-btn-login, button[type='submit']", force=True)

            print("DEBUG: Waiting for login processing and redirect...")
            await asyncio.sleep(10)

            # 4. CAPTURE & VERIFY
            if "/m/login" not in page.url:
                print(f"SUCCESS: Logged in! Current URL: {page.url}")
                storage = await context.storage_state()

                # Push the immortal session to MongoDB
                if DB_URI:
                    try:
                        client = MongoClient(DB_URI)
                        db = client['broker_db']
                        db.titan_auth.update_one(
                            {"account": USER_ID},
                            {
                                "$set": {
                                    "session_data": storage,
                                    "updated_at": datetime.utcnow()
                                }
                            },
                            upsert=True
                        )
                        client.close()
                        print("DEBUG: Immortal Session saved to MongoDB successfully.")
                    except Exception as mongo_err:
                        print(f"DEBUG: MongoDB Persistence error: {mongo_err}")

                await page.screenshot(path="artifacts/login_success.png")
            else:
                print("CRITICAL: Stuck on login screen.")
                await page.screenshot(path="artifacts/login_failed_final.png")

        except Exception as e:
            print(f"ERROR during login flow: {e}")
            await page.screenshot(path="artifacts/organic_flow_error.png")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_login())
