import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from spin_bot.playwright_client import PlaywrightClient

@pytest.mark.asyncio
async def test_apply_v21_ui_enhancements_injection():
    with patch('spin_bot.playwright_client.async_playwright'):
        client = PlaywrightClient("https://www.football.com")
        client.page = AsyncMock()

        await client._apply_v21_ui_enhancements()

        # Verify add_init_script was called with the V5.21 enhancement script
        client.page.add_init_script.assert_called()
        args, kwargs = client.page.add_init_script.call_args
        script_content = args[0]
        assert "Asset Resilience" in script_content
        assert "Theme-Based Loading UI" in script_content
        assert "Login required" in script_content
        assert "Z-Index Management" in script_content

@pytest.mark.asyncio
async def test_hide_init_loader_injection():
    with patch('spin_bot.playwright_client.async_playwright'):
        client = PlaywrightClient("https://www.football.com")
        client.page = AsyncMock()

        await client.hide_init_loader()

        # Verify evaluate was called to hide the loader
        client.page.evaluate.assert_called()
        args, kwargs = client.page.evaluate.call_args
        assert "app-init-loader-wrap" in args[0]
        assert "display = 'none'" in args[0]
