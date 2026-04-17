import os
import asyncio
import random
import json
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

async def handle_promos(page):
    """Checks for and dismisses promotional overlays like 'Flash Win'."""
    print("DEBUG: Checking for promotional overlays...")
    try:
        # 1. Target the 'Flash Win' specific popup
        # Common selectors for the promo: header text, the 'Check' button, or the 'X' close icon
        flash_win_selectors = [
            "text=Flash Win",
            "text=Flash Winning",
            "button:has-text('Check')",
            ".flash-win-header .close", # Guessing based on common patterns
            "button.m-btn-confirm" # Based on previous successes with confirm buttons
        ]

        for selector in flash_win_selectors:
            promo = page.locator(selector).first
            if await promo.is_visible(timeout=3000):
                print(f"DEBUG: Detected Flash Win popup via '{selector}' → closing...")

                # Attempt to click a close button or 'Check' button
                # We'll try the 'X' close button first if identifiable, otherwise the 'Check' button
                close_btn = page.locator(".m-icon-close, .icon-close, text=X, button:has-text('Check')").first
                if await close_btn.is_visible():
                    await close_btn.click(force=True)
                    print("DEBUG: Flash Win popup closed successfully")
                    await asyncio.sleep(2)
                    return True

        # 2. General dialog-wrapper fallback (Nuclear removal if interaction fails)
        popup_selector = ".dialog-wrapper, .m-dialog, .m-modal"
        if await page.locator(popup_selector).is_visible(timeout=2000):
            print("DEBUG: General popup detected. Removing from DOM...")
            await page.evaluate(f"document.querySelectorAll('{popup_selector}').forEach(el => el.remove())")
            await asyncio.sleep(1)
            return True

    except Exception as e:
        print(f"DEBUG: Promo check finished or bypassed: {e}")
    return False

async def run_login_and_recon():
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

        # 1. INITIAL POPUP HANDLING (Region selector etc)
        await handle_promos(page)

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
                        db.titan_auth.update_one({"account": USER_ID}, {"$set": {"session_data": storage, "updated_at": datetime.now(timezone.utc)}}, upsert=True)
                        client.close()
                    except Exception as mongo_err:
                        print(f"DEBUG: MongoDB error: {mongo_err}")

                # Telemetry 0: Homepage right after login
                await page.screenshot(path="artifacts/telemetry_0_homepage.png")
                await human_delay(2, 4)

                # 4. NAVIGATE TO GAMES LOBBY
                print("DEBUG: Navigating to Games section...")
                try:
                    games_btn = page.locator("text=Games").first
                    await games_btn.wait_for(state="visible", timeout=10000)
                    await games_btn.click(force=True)

                    print("DEBUG: Clicked Games. Waiting for lobby to load...")
                    await asyncio.sleep(5)

                    # SYSTEM ACTION: DISMISS BLOCKING OVERLAYS (Phase 27)
                    await handle_promos(page)

                    # 1. Full-Height Scroll Routine
                    print("DEBUG: Executing Full-Height Scroll Routine (3x)...")
                    for i in range(3):
                        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        print(f"DEBUG: Scrolled to bottom ({i+1}/3). Waiting for lazy-load...")
                        await human_delay(2, 4)

                    # 2. Extract Game Items
                    print("DEBUG: Extracting game items from grid...")
                    # Selector for game cards
                    game_selector = ".game-item, [class*='game-item'], [class*='game-list-item']"
                    game_items = page.locator(game_selector)
                    count = await game_items.count()
                    print(f"DEBUG: Found {count} game items in lobby")

                    games_data = []
                    for i in range(count):
                        item = game_items.nth(i)

                        # Extract basic info
                        name = await item.locator(".game-name, [class*='name']").first.text_content() if await item.locator(".game-name, [class*='name']").first.count() > 0 else "Unknown"
                        provider = await item.locator(".provider-name, [class*='provider']").first.text_content() if await item.locator(".provider-name, [class*='provider']").first.count() > 0 else "Unknown"
                        img_src = await item.locator("img").first.get_attribute("src") if await item.locator("img").first.count() > 0 else "N/A"
                        play_btn_text = await item.locator("button, .play-btn").first.text_content() if await item.locator("button, .play-btn").first.count() > 0 else "N/A"
                        html_snippet = await item.inner_html()

                        game_info = {
                            "name": name.strip() if name else "N/A",
                            "provider": provider.strip() if provider else "N/A",
                            "img_url": img_src,
                            "button_text": play_btn_text.strip() if play_btn_text else "N/A"
                        }
                        games_data.append(game_info)
                        print(f"GAME DETECTED: {game_info['name']} | Studio: {game_info['provider']} | Button: {game_info['button_text']}")

                        # Log snippet for the first few or target games
                        if "Spin" in game_info['name'] or "Bottle" in game_info['name'] or i < 3:
                             print(f"DEBUG: HTML Snippet for {game_info['name']}: {html_snippet[:200]}...")

                    # 3. Clean Telemetry Screenshot
                    print("DEBUG: Capturing clean games lobby screenshot...")
                    await page.screenshot(path="artifacts/telemetry_4_games_lobby_clean.png", full_page=True)

                    # Save Grid HTML
                    grid_container = page.locator(".game-list-container, .game-grid, [class*='game-list']").first
                    if await grid_container.is_visible():
                        lobby_html = await grid_container.inner_html()
                        with open("artifacts/full_lobby_grid.html", "w", encoding="utf-8") as f:
                            f.write(lobby_html)

                    # Save full data as JSON for debugging
                    with open("artifacts/games_data.json", "w", encoding="utf-8") as f:
                        json.dump(games_data, f, indent=2)

                except Exception as e:
                    print(f"ERROR during Games navigation/recon: {e}")
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
    asyncio.run(run_login_and_recon())
