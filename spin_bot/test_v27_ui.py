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
async def test_v27_titan_pathfinder_ua():
    with patch('spin_bot.playwright_client.async_playwright') as mock_ap:
        mock_pw = MagicMock()
        mock_ap.return_value.start = AsyncMock(return_value=mock_pw)
        mock_browser = AsyncMock()
        mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)

        client = PlaywrightClient("https://www.football.com")
        with patch.object(client, '_apply_v21_ui_enhancements', AsyncMock()):
            await client.setup()

        # Verify Chrome Android UA
        args, kwargs = mock_browser.new_context.call_args
        assert "Chrome" in kwargs['user_agent']
        assert "Android" in kwargs['user_agent']

@pytest.mark.asyncio
async def test_v27_login_logic():
    with patch('spin_bot.playwright_client.async_playwright'):
        client = PlaywrightClient("https://www.football.com")
        client.page = MagicMock()
        client.page.locator = MagicMock()
        client._handle_overlays = AsyncMock()
        client._log_execution = MagicMock()
        client.capture_failure_artifact = AsyncMock()
        client.page.goto = AsyncMock()
        client.page.evaluate = AsyncMock()
        client.page.wait_for_selector = AsyncMock()
        client.page.wait_for_url = AsyncMock()

        # Mock locator for error messages
        mock_error = MagicMock()
        mock_error.first = MagicMock()
        mock_error.first.is_visible = AsyncMock(return_value=False)

        client.page.locator.return_value = mock_error

        with patch.dict('os.environ', {'FOOTBALL_NG_LOGIN': '12345', 'FOOTBALL_NG_PASS': 'pass'}):
            with patch('sys.exit'):
                # Mock asyncio.wait_for to avoid waiting forever
                with patch('asyncio.wait_for', AsyncMock()):
                    await client.login()

            # Check if wait_for_selector was called with expanded pathfinder selector
            client.page.wait_for_selector.assert_any_call(
                "input[type='tel'], input[placeholder*='Phone'], input[autocomplete='tel'], section[class*='login'] input, .un-input-wrapper input",
                state="visible",
                timeout=15000
            )

            # Check if page.evaluate was called for injection
            client.page.evaluate.assert_called()
            args, kwargs = client.page.evaluate.call_args
            script = args[0]
            assert "input[autocomplete='tel']" in script
            assert "section[class*='login'] input" in script
