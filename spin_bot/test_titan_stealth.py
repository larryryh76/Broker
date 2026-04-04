import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from spin_bot.titan_stealth import TitanStealthClient

@pytest.mark.asyncio
async def test_handle_region_trap_native_click():
    client = TitanStealthClient()
    client.page = MagicMock()

    # Mock finding the close button
    mock_close = MagicMock()
    # In the script it is self.page.locator(...).wait_for, .is_visible, .click
    mock_close.wait_for = AsyncMock()
    mock_close.is_visible = AsyncMock(return_value=True)
    mock_close.click = AsyncMock()

    client.page.locator.return_value = mock_close

    with patch('asyncio.sleep', AsyncMock()):
        await client.handle_region_trap()

    # Verify interaction with close button
    mock_close.click.assert_called()

@pytest.mark.asyncio
async def test_login_vue_mounting_delay():
    client = TitanStealthClient()
    client.page = MagicMock()
    client.setup_db = AsyncMock()
    client.load_storage_state = MagicMock(return_value=None)
    client.setup_browser = AsyncMock()
    client.handle_region_trap = AsyncMock()
    client.save_storage_state = MagicMock()
    client.human_type = AsyncMock()
    client.page.goto = AsyncMock()
    client.page.url = "login"

    # Set credentials
    client.phone = "123"
    client.password = "456"

    # Mock locator for balance
    mock_balance = MagicMock()
    mock_balance.is_visible = AsyncMock(return_value=False)

    client.page.locator.return_value = mock_balance
    client.page.wait_for_selector = AsyncMock()
    client.page.wait_for_url = AsyncMock()

    with patch('asyncio.sleep', AsyncMock()):
        await client.login()

    # Verify wait_for_selector was called for raw inputs
    client.page.wait_for_selector.assert_any_call("input[type='tel']", state="visible", timeout=10000)
    # Verify human_type was called for phone and password
    assert client.human_type.call_count == 2
