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

        # 1. HANDLE THE REGION SELECTOR POPUP (Step 1 & 2)
        try:
            print("DEBUG: Checking for the blocking popup...")
            popup_selector = ".dialog-wrapper, .m-dialog"

            # Wait a few seconds to see if the popup triggers
            if await page.locator(popup_selector).is_visible(timeout=6000):
                print("DEBUG: Popup detected! Step 1: Attempting to click the 'X' (close button)...")

                # Try common close button patterns
                close_selectors = [
                    ".m-icon-close",
                    ".icon-close",
                    ".close-btn",
                    "button:has(.icon-close)",
                    ".m-dialog .close",
                    ".dialog-wrapper .close"
                ]

                closed = False
                for sel in close_selectors:
                    close_btn = page.locator(sel).first
                    if await close_btn.is_visible():
                        print(f"DEBUG: Found close button with selector '{sel}'. Clicking...")
                        await close_btn.click(force=True)
                        await asyncio.sleep(2)
                        if not await page.locator(popup_selector).is_visible():
                            print("DEBUG: Popup successfully closed via UI interaction.")
                            closed = True
                            break

                # Step 2: The 'Nuclear' Fallback (DOM Removal)
                if not closed and await page.locator(popup_selector).is_visible():
                    print("DEBUG: Popup still visible. Executing Nuclear Fallback (DOM removal)...")
                    await page.evaluate(f"document.querySelectorAll('{popup_selector}').forEach(el => el.remove())")
                    await asyncio.sleep(1)
                    if not await page.locator(popup_selector).is_visible():
                        print("DEBUG: Popup physically removed from the DOM.")
            else:
                print("DEBUG: No blocking popup detected.")
        except Exception as e:
            print(f"DEBUG: Popup handling flow finished or bypassed: {e}")

        # 2. CLICK THE ACTUAL LOGIN BUTTON
        try:
            print("DEBUG: Attempting click on the Home Screen Login button...")
            login_selector = ".m-btn-login"
            await page.wait_for_selector(login_selector, timeout=10000)

            # Use forced click as backup if something else is still in the way
            await page.click(login_selector, force=True)

            # 3. FILL CREDENTIALS
            print("DEBUG: Waiting for the phone/password form to appear...")
            await page.wait_for_selector("input[type='tel']", timeout=10000)

            print("DEBUG: Form found. Entering credentials...")
            await page.fill("input[type='tel']", USER_ID)
            await page.fill("input[type='password']", PASSWORD)

            # Submit the form
            print("DEBUG: Clicking submit...")
            # Updated selector specifically for the login form's submit button
            await page.click("button.login-btn, [data-op='login-btn']", force=True)

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

        # Step 3: The Full Element Dump (Crucial Requirement)
        print("DEBUG: Capturing full page elements dump...")
        try:
            content = await page.content()
            with open("artifacts/full_page_elements_dump.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("DEBUG: Full HTML dump saved to artifacts/full_page_elements_dump.html")
        except Exception as e:
            print(f"DEBUG: Failed to save HTML dump: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_login())
