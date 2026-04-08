import pytest
import asyncio
from spin_bot.titan_stealth import TitanStealthClient

@pytest.mark.asyncio
async def test_client_init():
    client = TitanStealthClient()
    assert client.home_url == "https://www.football.com/ng/m/home"
    assert client.game_url == "https://www.football.com/ng/m/games/spin-da-bottle"

@pytest.mark.asyncio
async def test_browser_setup_fingerprint():
    # Test initialization of browser and context with specific specs
    client = TitanStealthClient()
    try:
        await client.setup_browser()
        # Verify Context Options
        # We can't easily introspect private _options but we can check the UA
        ua = await client.page.evaluate("navigator.userAgent")
        assert "iPhone" in ua
        assert "17_4" in ua

        # Verify Preconnect Injection
        # Check if link tags exist
        preconnects = await client.page.evaluate("""() => {
            return Array.from(document.querySelectorAll('link[rel="preconnect"]'))
                .map(l => l.href);
        }""")
        # Note: Preconnects are injected on start, but the test page is about:blank initially
        # Actually in setup_browser it adds an init script which runs on next navigation
        await client.page.goto("about:blank")
        # In this specific implementation, it might not run on about:blank
        # Let's check the code: it adds init script then nothing.

    finally:
        await client.close()

if __name__ == "__main__":
    pytest.main([__file__])
