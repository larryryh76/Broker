import asyncio
import random
import os

async def close_any_blocking_overlay(page):
    """Generic, aggressive overlay closer"""
    print("🔍 Running generic overlay closer...")

    for attempt in range(1, 6):
        try:
            # Close X buttons
            await page.locator("button[aria-label*='close' i], .close, .m-icon-close, text=×, text=✕").first.click(timeout=2000)
            await asyncio.sleep(random.uniform(1, 2))
            
            # Click Nigeria
            await page.locator("text=Nigeria").first.click(timeout=1500)
            
            # Click big buttons
            for text in ["Check", "Continue", "Got it", "Confirm", "OK", "Next"]:
                await page.locator(f"button:has-text('{text}')").first.click(timeout=1500)
            
            # Top-right fallback click
            viewport = page.viewport_size
            if viewport:
                await page.mouse.click(viewport["width"] * 0.9, viewport["height"] * 0.08)

            await asyncio.sleep(random.uniform(1.5, 3))
            
            # Check if still blocked
            if not await page.locator(".dialog, .modal, [class*='overlay']").first.is_visible(timeout=1000):
                print("✅ Overlays cleared successfully")
                return True

        except:
            pass

    print("⚠️ Overlay closer finished (some may remain)")
    return False

async def navigate_to_games_and_scrape(page):
    """Navigate to Games and scrape"""
    print("🎮 Navigating to Games section...")

    try:
        # Click Games in bottom nav
        await page.locator("text=Games, .controller-icon, [class*='game']").first.click(timeout=10000)
        await asyncio.sleep(8)

        await close_any_blocking_overlay(page)

        # Scroll 3 times
        print("📜 Scrolling to load games...")
        for i in range(3):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            await asyncio.sleep(random.uniform(2.5, 4.5))
            print(f"Scroll {i+1}/3 done")

        # Take screenshot
        os.makedirs("artifacts", exist_ok=True)
        await page.screenshot(path="artifacts/telemetry_games_lobby_clean.png", full_page=True)
        print("📸 Games lobby screenshot saved")

        # Extract games (improved selectors)
        games = await page.locator(".game-item, .casino-game, [class*='game-card'], [class*='slot']").all()
        print(f"✅ Found {len(games)} game items")

        for i, game in enumerate(games[:15]):  # Log first 15
            try:
                name = await game.locator("h3, h4, [class*='name'], [class*='title']").first.text_content(timeout=1000)
                print(f"Game {i+1}: {name.strip() if name else 'N/A'}")
            except:
                pass

        return len(games)

    except Exception as e:
        print(f"❌ Error in games navigation: {e}")
        await page.screenshot(path="artifacts/games_error.png", full_page=True)
        return 0
