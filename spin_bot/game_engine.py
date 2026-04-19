import asyncio
import random
import os
import json

async def close_any_blocking_overlay(page):
    """
    Robust, generic popup/overlay handler.
    Attempts to close any full-screen or blocking overlay using multiple strategies.
    """
    overlay_selectors = [
        ".dialog-wrapper", ".m-dialog", ".m-modal",
        "[class*='overlay']", "[class*='promo']", "[class*='modal']"
    ]

    for attempt in range(1, 5):
        # 1. Check if any overlay is actually visible
        is_blocked = False
        for sel in overlay_selectors:
            if await page.locator(sel).first.is_visible(timeout=1000):
                is_blocked = True
                break

        if not is_blocked:
            # Check for high z-index elements that might not match selectors but cover screen
            # (Simple heuristic: check for common 'Check', 'Confirm', 'Nigeria' buttons)
            if not await page.locator("button:has-text('Check'), text=Nigeria, .m-icon-close").first.is_visible(timeout=500):
                if attempt == 1:
                    print("DEBUG: No overlay detected")
                return True

        print(f"DEBUG: Blocking overlay detected → attempting to close (attempt {attempt}/4)")
        try:
            # 2. Look for and click close patterns
            close_targets = [
                ".m-icon-close", ".icon-close", ".close-btn", "text=×", "text=X",
                "[class*='close']", "button:has-text('Confirm')", "button:has-text('OK')",
                "button:has-text('Got it')", "button:has-text('Check')", "button:has-text('Continue')",
                "button:has-text('Next')", "button:has-text('Okay')", "text=Nigeria",
                "button[class*='confirm']", "button[class*='btn-green']"
            ]

            for target in close_targets:
                el = page.locator(target).first
                if await el.is_visible(timeout=1000):
                    print(f"DEBUG: Clicking possible close/confirm element '{target}'...")
                    await el.click(force=True)
                    await asyncio.sleep(random.uniform(1.5, 3.0))
                    break # Re-evaluate overlay presence in next attempt

            # 3. Fallback: Coordinate-based click (Top-Right area, ~90% width, 10% height)
            if await page.locator(overlay_selectors[0]).first.is_visible(timeout=500):
                viewport = page.viewport_size
                if viewport:
                    x, y = viewport['width'] * 0.90, viewport['height'] * 0.10
                    print(f"DEBUG: Fallback: Attempting coordinate click at ({x}, {y})")
                    await page.mouse.click(x, y)
                    await asyncio.sleep(random.uniform(1.2, 2.5))

            # Verify if still visible
            still_visible = False
            for sel in overlay_selectors:
                if await page.locator(sel).first.is_visible(timeout=500):
                    still_visible = True
                    break

            if not still_visible:
                print("DEBUG: Overlay closed successfully")
                return True

        except Exception as e:
            print(f"DEBUG: Error in close_any_blocking_overlay attempt {attempt}: {e}")

    return False

async def navigate_to_games_and_scrape(page):
    """
    Navigates to the Games Lobby, handles blocking popups,
    and scrapes all visible game items.
    """
    print("DEBUG: Initiating navigation to Games Lobby...")

    try:
        # 1. Click the Games button in bottom navigation
        # Common selectors for the games controller icon in mobile nav
        games_nav_selector = "a[href*='/m/games/'], .m-nav-item:has-text('Games'), [class*='controller']"
        games_btn = page.locator(games_nav_selector).first
        await games_btn.wait_for(state="visible", timeout=10000)
        await games_btn.click(force=True)

        # 2. Wait up to 10 seconds for the page to settle
        print("DEBUG: Waiting 10 seconds for lobby/overlays to load...")
        await asyncio.sleep(10)

        # 3. Call robust generic overlay handler
        await close_any_blocking_overlay(page)

        # 4. Full-Height Scroll Routine (3x)
        print("DEBUG: Executing Full-Height Scroll Routine (3x)...")
        for i in range(1, 4):
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            print(f"DEBUG: Scroll cycle {i}/3 complete. Waiting for lazy-load...")
            await asyncio.sleep(random.uniform(2.5, 4.5))

        # 5. Extract Detailed Game Items
        print("DEBUG: Extracting all game items from the lobby grid...")
        # Comprehensive list of potential game item selectors
        item_selectors = [
            ".game-item", ".casino-game", "[class*='game-card']",
            "[class*='game-list-item']", ".slot-item", "div[data-v-app] .grid-item"
        ]

        game_elements = None
        for sel in item_selectors:
            if await page.locator(sel).count() > 0:
                game_elements = page.locator(sel)
                print(f"DEBUG: Using selector '{sel}' for extraction.")
                break

        extracted_games = []
        if game_elements:
            count = await game_elements.count()
            print(f"DEBUG: Found {count} game items in lobby")

            for i in range(count):
                item = game_elements.nth(i)
                try:
                    # Target metadata using generic patterns
                    name = await item.locator("[class*='name'], [class*='title'], h3, h4").first.text_content() if await item.locator("[class*='name'], [class*='title'], h3, h4").first.count() > 0 else "N/A"
                    provider = await item.locator("[class*='provider'], [class*='studio'], [class*='vendor']").first.text_content() if await item.locator("[class*='provider'], [class*='studio'], [class*='vendor']").first.count() > 0 else "N/A"
                    img_src = await item.locator("img").first.get_attribute("src") if await item.locator("img").first.count() > 0 else "N/A"
                    play_btn = await item.locator("button, .play-btn, [class*='btn']").first.text_content() if await item.locator("button, .play-btn, [class*='btn']").first.count() > 0 else "N/A"

                    game_info = {
                        "name": name.strip() if name else "N/A",
                        "provider": provider.strip() if provider else "N/A",
                        "thumbnail": img_src,
                        "button_text": play_btn.strip() if play_btn else "N/A"
                    }
                    extracted_games.append(game_info)
                    if i < 10 or "Spin" in game_info['name']: # Log a sample
                        print(f"GAME DETECTED: {game_info['name']} (Provider: {game_info['provider']})")
                except Exception as e:
                    print(f"DEBUG: Skipping game item {i} due to extraction error: {e}")
        else:
            print("DEBUG: WARNING: Found 0 game items using standard selectors.")

        # 6. Capture Telemetry & HTML Dumps
        print("DEBUG: Capturing clean games lobby telemetry screenshot...")
        os.makedirs("artifacts", exist_ok=True)
        await page.screenshot(path="artifacts/telemetry_5_games_lobby_clean.png", full_page=True)

        print("DEBUG: Saving grid HTML for debugging...")
        try:
            # Try to capture the most relevant container
            container_sel = ".game-list-container, .game-grid, [class*='game-list'], [class*='lobby-container']"
            container = page.locator(container_sel).first
            grid_html = await container.inner_html() if await container.is_visible() else await page.content()
            with open("artifacts/games_lobby_recon_dump.html", "w", encoding="utf-8") as f:
                f.write(grid_html)
        except Exception as e:
            print(f"DEBUG: Failed to capture targeted grid HTML: {e}")

        return extracted_games

    except Exception as e:
        print(f"ERROR in navigate_to_games_and_scrape: {e}")
        await page.screenshot(path="artifacts/games_lobby_fatal_error.png")
        return []
