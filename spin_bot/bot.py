import os
import asyncio
import random
from playwright.async_api import async_playwright
from pymongo import MongoClient
from datetime import datetime, timezone

# Environment Secrets
DB_URI = os.getenv("MONGODB_URI")
USER_ID = os.getenv("FOOTBALL_NG_LOGIN")
PASSWORD = os.getenv("FOOTBALL_NG_PASS")

async def human_delay(min_sec=2, max_sec=5):
    """Helper function for randomized 'thinking' time."""
    delay = random.uniform(min_sec, max_sec)
    print(f"DEBUG: Human delay for {delay:.2f}s...")
    await asyncio.sleep(delay)

async def run_login_and_navigate():
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
            print("DEBUG: Checking for the blocking popup...")
            popup_selector = ".dialog-wrapper, .m-dialog"
            if await page.locator(popup_selector).is_visible(timeout=6000):
                close_selectors = [".m-icon-close", ".icon-close", ".close-btn", "button:has(.icon-close)", ".m-dialog .close", ".dialog-wrapper .close"]
                closed = False
                for sel in close_selectors:
                    close_btn = page.locator(sel).first
                    if await close_btn.is_visible():
                        await close_btn.click(force=True)
                        await asyncio.sleep(2)
                        if not await page.locator(popup_selector).is_visible():
                            closed = True
                            break
                if not closed and await page.locator(popup_selector).is_visible():
                    await page.evaluate(f"document.querySelectorAll('{popup_selector}').forEach(el => el.remove())")
                    await asyncio.sleep(1)
        except Exception as e:
            print(f"DEBUG: Popup handling flow finished or bypassed: {e}")

        # 2. LOGIN FLOW
        try:
            print("DEBUG: Clicking Home Screen Login button...")
            await page.wait_for_selector(".m-btn-login", timeout=10000)
            await page.click(".m-btn-login", force=True)

            await page.wait_for_selector("input[type='tel']", timeout=10000)
            await page.fill("input[type='tel']", USER_ID)
            await page.fill("input[type='password']", PASSWORD)

            print("DEBUG: Clicking submit...")
            await page.click("button.login-btn, [data-op='login-btn']", force=True)

            print("DEBUG: Waiting for login processing...")
            await asyncio.sleep(10)

            if "/m/login" not in page.url:
                print(f"SUCCESS: Logged in! Current URL: {page.url}")
                storage = await context.storage_state()

                # Persist Session (Updated with timezone-aware datetime)
                if DB_URI:
                    try:
                        client = MongoClient(DB_URI)
                        db = client['broker_db']
                        db.titan_auth.update_one(
                            {"account": USER_ID},
                            {
                                "$set": {
                                    "session_data": storage,
                                    "updated_at": datetime.now(timezone.utc)
                                }
                            },
                            upsert=True
                        )
                        client.close()
                    except Exception as mongo_err:
                        print(f"DEBUG: MongoDB error: {mongo_err}")

                # Telemetry 0: Homepage right after login
                await page.screenshot(path="artifacts/telemetry_0_homepage.png")
                await human_delay(2, 4)

                # Natural Scrolling Simulation
                print("DEBUG: Simulating human scroll...")
                await page.mouse.wheel(0, 400)
                await page.screenshot(path="artifacts/telemetry_1_scrolling.png")
                await human_delay(1, 2)
                await page.mouse.wheel(0, -400)
                await human_delay(2, 4)

                # 4. NAVIGATE TO VIRTUALS (Primary Navigation Fix)
                print("DEBUG: Navigating to Virtuals section...")
                try:
                    # Target Virtuals lobby or link
                    virtuals_btn = page.locator("a[href*='virtuals-lobby']").first
                    if not await virtuals_btn.is_visible():
                         virtuals_btn = page.get_by_role("link", name="Virtuals")

                    await virtuals_btn.wait_for(state="visible", timeout=10000)
                    await virtuals_btn.click(force=True)

                    print("DEBUG: Clicked Virtuals. Waiting for lobby to load...")
                    await asyncio.sleep(random.uniform(4.0, 6.5))

                    # Telemetry 2: The Virtuals/Game Lobby
                    await page.screenshot(path="artifacts/telemetry_2_virtuals_lobby.png")

                except Exception as e:
                    print(f"ERROR: Failed to navigate to Virtuals: {e}")
                    await page.screenshot(path="artifacts/virtuals_nav_error.png")

                    # 5. DIAGNOSTIC ROUTINE
                    print("DEBUG: Diagnostic Routine triggered. Checking for 'Lite' version...")
                    snap_nav = await page.locator(".m-snap-nav").count()
                    if snap_nav > 0:
                        print("DEBUG: ALERT: 'm-snap-nav' detected. Page might be in 'Lite' mode.")

                    html_content = await page.content()
                    with open("artifacts/diagnostic_lite_check_dump.html", "w", encoding="utf-8") as f:
                        f.write(html_content)

                # 6. CAPTURE THE LOBBY DUMP
                print("DEBUG: Capturing lobby dump of current screen...")
                html_content = await page.content()
                with open("artifacts/casino_lobby_dump.html", "w", encoding="utf-8") as f:
                    f.write(html_content)

            else:
                print("CRITICAL: Stuck on login screen.")
                await page.screenshot(path="artifacts/login_failed_final.png")

        except Exception as e:
            print(f"ERROR during flow: {e}")
            await page.screenshot(path="artifacts/organic_flow_error.png")

        # Final Element Dump
        print("DEBUG: Capturing full page elements dump...")
        try:
            content = await page.content()
            with open("artifacts/full_page_elements_dump.html", "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            print(f"DEBUG: Failed to save HTML dump: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_login_and_navigate())
