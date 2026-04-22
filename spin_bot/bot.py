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
        
        body_text = await page.evaluate("document.body.innerText")
        with open(f"artifacts/{step_name}_text.txt", "w", encoding="utf-8") as f:
            f.write(f"=== STEP: {step_name} ===\n")
            f.write(f"URL: {page.url}\n")
            f.write(f"Title: {await page.title()}\n")
            f.write(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write("=== VISIBLE TEXT ===\n")
            f.write(body_text[:15000])  # Limit size
        
        print(f"✅ Saved {step_name} data")
    except Exception as e:
        print(f"⚠️ Save failed for {step_name}: {e}")

async def close_location_preference(page):
    print("🔍 Handling Location Preference...")
    for attempt in range(1, 7):
        try:
            nigeria = page.locator("text=Nigeria").first
            if await nigeria.is_visible(timeout=6000):
                await nigeria.click(force=True)
                print(f"✅ Clicked Nigeria (attempt {attempt})")
                await asyncio.sleep(random.uniform(4, 6))
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

        # Stronger loading strategy
        print("🌍 Loading football.com with JS enabled...")
        await page.goto("https://www.football.com/ng/m/", 
                       wait_until="domcontentloaded", 
                       timeout=90000)
        
        await asyncio.sleep(6)
        await save_page_data(page, "00_initial_load")

        # Handle location modal
        await close_location_preference(page)
        await asyncio.sleep(4)
        await save_page_data(page, "01_after_location")

        # Login attempt
        print("🔑 Attempting to click Login...")
        try:
            login_selectors = [
                "button:has-text('Login')", 
                "button:has-text('Log In')", 
                ".m-btn-login", 
                "[data-op='nav-login']"
            ]
            for sel in login_selectors:
                try:
                    await page.locator(sel).first.click(timeout=8000, force=True)
                    print(f"✅ Clicked using: {sel}")
                    break
                except:
                    continue

            await asyncio.sleep(5)
            await save_page_data(page, "02_login_form_attempt")

            # Try to fill form anyway
            try:
                await page.locator("input[type='tel'], input[placeholder*='phone' i]").fill(USER_ID)
                await page.locator("input[type='password']").fill(PASSWORD)
                print("✅ Filled credentials")
                await page.locator("button:has-text('Log In'), button[type='submit']").first.click()
            except:
                print("Could not find login fields yet")

            await asyncio.sleep(12)
            await save_page_data(page, "03_after_submit")

        except Exception as e:
            print(f"Login phase error: {e}")
            await save_page_data(page, "login_error")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_bot())
