import os
import asyncio
import random
from playwright.async_api import async_playwright
from pymongo import MongoClient
from datetime import datetime, timezone

# Import game engine
from game_engine import navigate_to_games_and_scrape

DB_URI = os.getenv("MONGODB_URI")
USER_ID = os.getenv("FOOTBALL_NG_LOGIN")
PASSWORD = os.getenv("FOOTBALL_NG_PASS")

async def save_page_data(page, filename):
    """Save useful page data for analysis"""
    try:
        # Take screenshot
        await page.screenshot(path=f"artifacts/{filename}.png", full_page=True)
        
        # Save full HTML
        html = await page.content()
        with open(f"artifacts/{filename}.html", "w", encoding="utf-8") as f:
            f.write(html)
        
        # Save clean text version (what I can read easily)
        text_content = await page.text_content("body")
        visible_text = "\n".join([line.strip() for line in text_content.splitlines() if line.strip()])
        
        with open(f"artifacts/{filename}_text.txt", "w", encoding="utf-8") as f:
            f.write(f"=== PAGE: {filename} ===\n")
            f.write(f"URL: {page.url}\n")
            f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("=== VISIBLE TEXT ===\n")
            f.write(visible_text)
        
        print(f"📄 Saved data for {filename} (screenshot + text + html)")
    except Exception as e:
        print(f"⚠️ Failed to save page data: {e}")

async def close_location_preference(page):
    """Dedicated handler for Location Preference"""
    print("🔍 Looking for Location Preference modal...")
    for attempt in range(1, 6):
        try:
            nigeria = page.locator("text=Nigeria").first
            if await nigeria.is_visible(timeout=5000):
                print(f"✅ Attempt {attempt}: Clicking Nigeria...")
                await nigeria.click(force=True)
                await asyncio.sleep(random.uniform(3, 5))
                return True
        except:
            pass
        await asyncio.sleep(2)
    print("⚠️ Location modal handling finished")
    return False

async def run_bot():
    if not all([USER_ID, PASSWORD, DB_URI]):
        print("❌ Missing secrets.")
        return

    os.makedirs("artifacts", exist_ok=True)

    async with async_playwright() as p:
        device = p.devices["iPhone 13"]
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(**device)
        page = await context.new_page()

        print("🌍 Navigating to football.com...")
        await page.goto("https://www.football.com/ng/m/", wait_until="networkidle", timeout=60000)
        await save_page_data(page, "00_homepage_before_login")

        await asyncio.sleep(random.uniform(3, 5))

        # Handle Location Preference
        await close_location_preference(page)
        await save_page_data(page, "01_after_location_modal")

        # === LOGIN ===
        print("🔑 Starting login...")
        try:
            await page.locator("button:has-text('Log'), button:has-text('Login'), .m-btn-login, [data-op='nav-login']").first.click(timeout=20000, force=True)
            print("✅ Clicked Login button")
            await asyncio.sleep(random.uniform(3, 5))
            await save_page_data(page, "02_login_form")

            # Fill form
            await page.locator("input[type='tel'], input[placeholder*='phone' i]").fill(USER_ID)
            await page.locator("input[type='password']").fill(PASSWORD)
            print("✅ Filled credentials")

            await page.locator("button:has-text('Log In'), button:has-text('Login'), button[type='submit']").first.click()
            print("✅ Submitted login")

            await asyncio.sleep(12)
            await save_page_data(page, "03_after_login_attempt")

            if "login" not in page.url.lower():
                print(f"✅ SUCCESS: Logged in! Current URL: {page.url}")
                
                # Save session
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
                    print(f"⚠️ MongoDB error: {e}")

                await save_page_data(page, "04_login_success")

                # Go to Games
                await asyncio.sleep(random.uniform(3, 5))
                await navigate_to_games_and_scrape(page)

            else:
                print("❌ Still on login page")
                await save_page_data(page, "login_failed")

        except Exception as e:
            print(f"❌ Login error: {e}")
            await save_page_data(page, "login_error")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
