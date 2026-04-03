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

@pytest.mark.asyncio
async def test_v26_pathfinder_logic():
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

            # Check if direct navigation was triggered
            client.page.goto.assert_called_with("https://www.football.com/ng/m/independent_login", wait_until="networkidle")

            # Check if wait_for_selector was called with pathfinder selector
            client.page.wait_for_selector.assert_any_call("input[type='tel'], input[placeholder*='Phone'], .un-input-wrapper input", state="visible", timeout=8000)

            # Check if page.evaluate was called for injection
            client.page.evaluate.assert_called()
            args, kwargs = client.page.evaluate.call_args
            script = args[0]
            assert "tel.dispatchEvent" in script
            assert "pwd.dispatchEvent" in script
            assert "setTimeout" in script
