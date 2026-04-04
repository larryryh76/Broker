import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from spin_bot.titan_stealth import TitanStealthClient

@pytest.mark.asyncio
async def test_ui_sensitivity_injections():
    client = TitanStealthClient()
    client.page = MagicMock()
    client.page.route = AsyncMock()
    client.page.add_init_script = AsyncMock()

    await client._apply_ui_and_interception()

    # Verify both route and add_init_script were called
    client.page.route.assert_called()
    client.page.add_init_script.assert_called()

    # Verify script content for V5.21 requirements
    args, _ = client.page.add_init_script.call_args
    script = args[0]
    assert "Asset Resilience" in script
    assert "applyThemeStyle" in script
    assert "triggerLoginModal" in script
    assert "zIndex" in script

@pytest.mark.asyncio
async def test_interceptor_discovery():
    client = TitanStealthClient()

    # Mock a request
    req = MagicMock()
    req.url = "https://www.football.com/api/ng/auth/login"
    req.method = "POST"

    await client._on_request(req)
    assert client.discovered_login_url == req.url

@pytest.mark.asyncio
async def test_golden_ticket_immediate_save():
    client = TitanStealthClient()
    client.page = MagicMock()
    client.page.url = "https://www.football.com/ng/m/me"
    client.context = MagicMock()
    client.context.storage_state = AsyncMock(return_value={})
    client.save_storage_state = MagicMock()

    mock_frame = MagicMock()
    client.page.main_frame = mock_frame

    await client._on_framenavigated(mock_frame)
    client.save_storage_state.assert_called()

@pytest.mark.asyncio
async def test_native_modal_resolution():
    client = TitanStealthClient()
    client.page = MagicMock()
    client.page.evaluate = AsyncMock(return_value="complete")
    client.page.wait_for_load_state = AsyncMock()

    mock_nigeria = MagicMock()
    mock_nigeria.wait_for = AsyncMock()
    mock_nigeria.is_visible = AsyncMock(return_value=True)
    mock_nigeria.click = AsyncMock()

    client.page.locator.return_value.filter.return_value.first = mock_nigeria

    with patch('asyncio.sleep', AsyncMock()):
        await client.handle_region_trap()

    mock_nigeria.click.assert_called()
