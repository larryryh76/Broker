import os
import asyncio
import random
from playwright.async_api import async_playwright
from pymongo import MongoClient
from datetime import datetime, timezone

from game_engine import navigate_to_games_and_scrape

DB_URI = os.getenv("MONGODB_URI")
USER_ID = os.getenv("FOOTBALL_NG_LOGIN")
PASSWORD = os.getenv("FOOTBALL_NG_PASS")

async def save_page_data(page, step_name):
    os.makedirs("artifacts", exist_ok=True)
    try:
        await page.screenshot(path=f"artifacts/{step_name}.png", full_page=True)
        html = await page.content()
        with open(f"artifacts/{step_name}.html", "w", encoding="utf-8") as f:
            f.write(html)
        body_text = await page.evaluate("document.body.innerText || ''")
        with open(f"artifacts/{step_name}_text.txt", "w", encoding="utf-8") as f:
            f.write(f"=== STEP: {step_name} ===\nURL: {page.url}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(body_text[:20000])
        print(f"✅ Saved {step_name} data")
    except Exception as e:
        print(f"⚠️ Save error: {e}")

async def close_location_preference(page):
    print("🔍 Handling Location Preference modal...")
    for attempt in range(1, 8):
        try:
            nigeria = page.locator("text=Nigeria").first
            if await nigeria.is_visible(timeout=8000):
                await nigeria.click(force=True)
                print(f"✅ Clicked Nigeria (attempt {attempt})")
                await asyncio.sleep(random.uniform(5, 7))   # Longer wait
                return True
        except:
            pass
        await asyncio.sleep(2)
    print("⚠️ Location handling finished")
    return False

async def run_bot():
    if not all([USER_ID, PASSWORD, DB_URI]):
        print("❌ Missing secrets.")
        return

    async with async_playwright() as p:
        device = p.devices["iPhone 13"]
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            **device,
            bypass_csp=True,
            ignore_https_errors=True
        )
        page = await context.new_page()

        print("🌍 Loading football.com...")
        await page.goto("https://www.football.com/ng/m/", 
                       wait_until="domcontentloaded", timeout=90000)
        await asyncio.sleep(8)
        await save_page_data(page, "00_initial_load")

        # Handle modal
        await close_location_preference(page)
        await asyncio.sleep(6)
        await save_page_data(page, "01_after_location")

        # === LOGIN ===
        print("🔑 Attempting Login...")
        try:
            # Multiple attempts to open login
            login_selectors = [
                ".m-btn-login", 
                "[data-op='nav-login']",
                "button:has-text('Login')", 
                "button:has-text('Log In')",
                "text=Login"
            ]
            
            clicked = False
            for sel in login_selectors:
                try:
                    btn = page.locator(sel).first
                    if await btn.is_visible(timeout=5000):
                        await btn.click(force=True)
                        print(f"✅ Clicked login using: {sel}")
                        clicked = True
                        break
                except:
                    continue

            if not clicked:
                print("Trying coordinate click on top right Login area...")
                await page.mouse.click(340, 60)   # Approximate Login button position

            await asyncio.sleep(8)
            await save_page_data(page, "02_login_modal_opened")

            # Try to fill form
            try:
                phone_field = page.locator("input[type='tel'], input[placeholder*='phone' i], input[placeholder*='Phone']").first
                await phone_field.wait_for(state="visible", timeout=15000)
                await phone_field.fill(USER_ID)
                await page.locator("input[type='password']").fill(PASSWORD)
                print("✅ Filled login form")

                await page.locator("button:has-text('Log In'), button:has-text('Login'), button[type='submit']").first.click()
                print("✅ Submitted")
            except Exception as fill_err:
                print(f"Could not fill form yet: {fill_err}")

            await asyncio.sleep(15)
            await save_page_data(page, "03_after_submit")

            if "login" not in page.url.lower() and await page.locator("input[type='tel']").count() == 0:
                print(f"✅ SUCCESS: Logged in! URL: {page.url}")
                # Save session to MongoDB...
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
                    print(f"MongoDB error: {e}")

                await save_page_data(page, "04_login_success")
                await asyncio.sleep(4)
                await navigate_to_games_and_scrape(page)

            else:
                print("❌ Login not successful yet")
                await save_page_data(page, "login_still_failed")

        except Exception as e:
            print(f"Login phase error: {e}")
            await save_page_data(page, "login_crash")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
