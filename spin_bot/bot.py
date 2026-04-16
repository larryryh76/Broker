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

                # Persist Session
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

                # 4. NAVIGATE TO GAMES LOBBY
                print("DEBUG: Navigating to Games section...")
                try:
                    # Target Games lobby or link
                    games_btn = page.locator("a[href*='/ng/m/games/'], text=Games").first
                    await games_btn.wait_for(state="visible", timeout=10000)
                    await games_btn.click(force=True)

                    print("DEBUG: Clicked Games. Waiting for lobby to load...")
                    await asyncio.sleep(random.uniform(5.0, 8.0))

                    # Telemetry: The Games Lobby
                    await page.screenshot(path="artifacts/telemetry_2_games_lobby.png")

                    # Data Extraction: Games Lobby Dump
                    print("DEBUG: Capturing Games lobby dump...")
                    games_content = await page.content()
                    with open("artifacts/games_lobby_dump.html", "w", encoding="utf-8") as f:
                        f.write(games_content)
                except Exception as e:
                    print(f"ERROR: Failed to navigate to Games: {e}")
                    await page.screenshot(path="artifacts/games_nav_error.png")

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
