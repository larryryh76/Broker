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
        # Launch browser with mobile context
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            viewport={'width': 375, 'height': 812},
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 13_2_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/13.0.3 Mobile/15E148 Safari/04.1"
        )
        page = await context.new_page()

        print("Navigating to mobile home page: https://www.football.com/ng/m/ ...")
        await page.goto("https://www.football.com/ng/m/", wait_until="networkidle")

        # Check for livescore redirection (detection indicator)
        current_url = page.url
        if "livescore" in current_url:
            print(f"Warning: Redirected to {current_url}. Bot detection likely.")
            await page.screenshot(path="artifacts/redirect_detected.png")
            await browser.close()
            return

        # Handle potential popups (Gatekeeper Bypass)
        print("Checking for popups...")
        try:
            # Wait a bit for popups to appear
            await asyncio.sleep(3)
            popup_selectors = [".dialog-wrapper", ".m-dialog", ".m-modal"]
            for selector in popup_selectors:
                if await page.locator(selector).is_visible():
                    print(f"Popup detected ({selector}). Attempting to dismiss...")
                    # Try to find a confirm/close button
                    confirm_btn = page.locator(f"{selector} button:has-text('Confirm'), {selector} .m-btn-confirm, {selector} button:has-text('OK'), {selector} .close-btn")
                    if await confirm_btn.is_visible():
                        await confirm_btn.click()
                        print("Popup dismissed.")
                    else:
                        print("Could not find a dismissal button for the popup.")
        except Exception as e:
            print(f"Error handling popups: {e}")

        print("Proceeding to find login button...")
        try:
            login_btn = page.locator(".m-btn-login")
            await login_btn.wait_for(state="visible", timeout=10000)

            # Try normal click first, then forced, then JS
            try:
                print("Attempting normal click on login button...")
                await login_btn.click(timeout=5000)
            except Exception:
                print("Normal click failed or timed out. Attempting forced click...")
                try:
                    await login_btn.click(force=True, timeout=5000)
                except Exception:
                    print("Forced click failed. Using JavaScript injection fallback...")
                    await page.evaluate("document.querySelector('.m-btn-login').click()")

            print("Login button interaction complete.")
        except Exception as e:
            print(f"Login button error: {e}")
            await page.screenshot(path="artifacts/home_page_error.png")
            await browser.close()
            return

        # Fill login details
        print("Filling login credentials...")
        try:
            # Targeting mobile/password fields on the login page
            await page.wait_for_selector('input[type="tel"]', timeout=10000)
            await page.fill('input[type="tel"]', login_phone)
            await page.fill('input[type="password"]', login_pass)

            print("Submitting login...")
            # Click the login submission button
            await page.click('button:has-text("Login"), button[type="submit"]', force=True)
        except Exception as e:
            print(f"Login field error: {e}")
            await page.screenshot(path="artifacts/login_field_error.png")
            await browser.close()
            return

        # Wait for navigation/successful login indicator
        print("Waiting 10 seconds for login to complete and hydration...")
        await asyncio.sleep(10)

        # Verification Screenshot
        print("Capturing verification screenshot: login_confirmed.png")
        await page.screenshot(path="artifacts/login_confirmed.png", full_page=True)

        # Persist Session
        print("Capturing storage state...")
        storage = await context.storage_state()

        print("Persisting session to MongoDB...")
        try:
            client = MongoClient(mongo_uri)
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
