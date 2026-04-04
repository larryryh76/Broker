import pytest
import time
from unittest.mock import AsyncMock, MagicMock, patch
from spin_bot.titan_stealth import TitanStealthClient

@pytest.mark.asyncio
async def test_api_login_fallback_logic():
    client = TitanStealthClient()
    client.context = MagicMock()
    client.context.request = AsyncMock()
    client.context.storage_state = AsyncMock(return_value={})
    client.save_storage_state = MagicMock()

    client.phone = "123"
    client.password = "456"

    # Mock successful API response
    mock_res = MagicMock()
    mock_res.status = 200
    client.context.request.post.return_value = mock_res

    success = await client.api_login_fallback()

    assert success is True
    client.context.request.post.assert_called()
    client.save_storage_state.assert_called()

@pytest.mark.asyncio
async def test_login_scroll_and_fallback():
    client = TitanStealthClient()
    client.page = MagicMock()
    client.setup_db = AsyncMock()
    client.load_storage_state = MagicMock(return_value=None)
    client.setup_browser = AsyncMock()
    client.handle_region_trap = AsyncMock()
    client.api_login_fallback = AsyncMock(return_value=True)

    client.page.goto = AsyncMock()
    client.page.url = "login"
    client.page.locator.return_value.is_visible = AsyncMock(return_value=False)

    # Mock timeout on first and second wait_for_selector to trigger scroll then fallback
    client.page.wait_for_selector = AsyncMock(side_effect=Exception("Timeout"))
    client.page.mouse = MagicMock()
    client.page.mouse.wheel = AsyncMock()

    with patch('asyncio.sleep', AsyncMock()):
        success = await client.login()

    assert success is True
    client.page.mouse.wheel.assert_called_with(0, 500)
    client.api_login_fallback.assert_called()
