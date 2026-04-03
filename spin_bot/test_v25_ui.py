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
async def test_v25_direct_injection_logic():
    with patch('spin_bot.playwright_client.async_playwright'):
        client = PlaywrightClient("https://www.football.com")
        client.page = MagicMock()
        client.page.locator = MagicMock()
        client._handle_overlays = AsyncMock()
        client._log_execution = MagicMock()
        client.capture_failure_artifact = AsyncMock()
        client.page.url = "https://www.football.com/ng/m/independent_login"
        client.page.goto = AsyncMock()
        client.page.click = AsyncMock()
        client.page.evaluate = AsyncMock()
        client.page.wait_for_selector = AsyncMock()
        client.page.wait_for_url = AsyncMock()

        # Mock locator for WAP triggers
        mock_trigger = MagicMock()
        mock_trigger.first = MagicMock()
        mock_trigger.first.wait_for = AsyncMock()
        mock_trigger.first.is_visible = AsyncMock(return_value=True)
        mock_trigger.first.click = AsyncMock()

        # Setup page.locator to return different things for different selectors
        def side_effect(selector):
            if selector == "text='Login'":
                m = MagicMock()
                m.first = mock_trigger.first
                return m
            elif "error" in selector:
                m = MagicMock()
                m.first = MagicMock(is_visible=AsyncMock(return_value=False))
                return m
            else:
                m = MagicMock()
                m.first = mock_trigger.first
                return m

        client.page.locator.side_effect = side_effect

        with patch.dict('os.environ', {'FOOTBALL_NG_LOGIN': '12345', 'FOOTBALL_NG_PASS': 'pass'}):
            with patch('sys.exit'):
                # Mock asyncio.wait_for to avoid waiting forever
                with patch('asyncio.wait_for', AsyncMock()):
                    await client.login()

            # Check if wait_for_selector was called for input[type='tel'] with state='attached'
            client.page.wait_for_selector.assert_any_call("input[type='tel'], .un-input-wrapper input", state="attached", timeout=5000)

            # Check if page.evaluate was called (this is the direct injection)
            client.page.evaluate.assert_called()
            args, kwargs = client.page.evaluate.call_args
            script = args[0]
            assert "dispatchEvent" in script
            assert "phoneInput.value = u" in script
            assert "passInput.value = p" in script
