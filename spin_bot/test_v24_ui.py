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
async def test_v24_login_logic():
    with patch('spin_bot.playwright_client.async_playwright'):
        client = PlaywrightClient("https://www.football.com")
        client.page = MagicMock()
        client.page.locator = MagicMock()
        client._handle_overlays = AsyncMock()
        client._log_execution = MagicMock()
        client.capture_failure_artifact = AsyncMock()
        client.page.url = "https://www.football.com/ng/m/independent_login"
        client.page.goto = AsyncMock()

        # Mock locator to return visible triggers
        mock_trigger = MagicMock()
        mock_trigger.first = MagicMock()
        mock_trigger.first.wait_for = AsyncMock()
        mock_trigger.first.is_visible = AsyncMock(return_value=True)
        mock_trigger.first.click = AsyncMock()

        # Mock input fields
        mock_phone = MagicMock()
        mock_phone.wait_for = AsyncMock()
        mock_phone.click = AsyncMock()
        mock_phone.fill = AsyncMock()
        mock_phone.is_visible = AsyncMock(return_value=True)

        mock_pass = MagicMock()
        mock_pass.fill = AsyncMock()

        mock_submit = MagicMock()
        mock_submit.click = AsyncMock()

        def side_effect(selector):
            if "input" in selector or "Phone" in selector or "Mobile" in selector or "tel" in selector or "un-input" in selector:
                m = MagicMock()
                m.first = mock_phone
                return m
            elif "password" in selector:
                m = MagicMock()
                m.first = mock_pass
                return m
            elif "button" in selector or "submit" in selector:
                m = MagicMock()
                m.first = mock_submit
                return m
            else:
                m = MagicMock()
                m.first = mock_trigger.first
                return m

        client.page.locator.side_effect = side_effect
        client.page.wait_for_selector = AsyncMock()
        client.page.wait_for_url = AsyncMock()

        with patch.dict('os.environ', {'FOOTBALL_NG_LOGIN': '12345', 'FOOTBALL_NG_PASS': 'pass'}):
            with patch('sys.exit'):
                # Mock asyncio.wait_for and asyncio.sleep
                with patch('asyncio.wait_for', AsyncMock()):
                    with patch('asyncio.sleep', AsyncMock()):
                        await client.login()

            # Check if at least one trigger was clicked
            assert mock_trigger.first.click.called
            # Check if phone was filled
            assert mock_phone.fill.called
            # Check if submit was clicked
            assert mock_submit.click.called
