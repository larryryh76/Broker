import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from spin_bot.titan_stealth import TitanStealthClient

@pytest.mark.asyncio
async def test_handle_region_trap_interaction():
    client = TitanStealthClient()
    client.page = MagicMock()
    client.page.wait_for_load_state = AsyncMock()

    # Mock finding the Nigeria item
    mock_nigeria = MagicMock()
    mock_nigeria.first = MagicMock()
    mock_nigeria.first.wait_for = AsyncMock()
    mock_nigeria.first.is_visible = AsyncMock(return_value=True)
    mock_nigeria.first.click = AsyncMock()

    # Set up the locator to return the nigeria item
    client.page.locator.return_value.filter.return_value = mock_nigeria

    with patch('asyncio.sleep', AsyncMock()):
        await client.handle_region_trap()

    # Verify interaction with Nigeria item
    mock_nigeria.first.click.assert_called_with(force=True)

@pytest.mark.asyncio
async def test_login_tab_switch_fallback():
    client = TitanStealthClient()
    client.page = MagicMock()
    client.setup_db = AsyncMock()
    client.load_storage_state = MagicMock(return_value=None)
    client.setup_browser = AsyncMock()
    client.handle_region_trap = AsyncMock()
    client.save_storage_state = MagicMock()
    client.human_type = AsyncMock()
    client.page.goto = AsyncMock()
    client.page.evaluate = AsyncMock(return_value="complete")
    client.page.url = "login"

    # Set credentials manually on the instance
    client.phone = "123"
    client.password = "456"

    # Mock locator for balance (check login status)
    mock_balance = MagicMock()
    mock_balance.is_visible = AsyncMock(return_value=False)

    # Mock locator for tabs
    mock_tab = MagicMock()
    mock_tab.first = MagicMock()
    mock_tab.first.is_visible = AsyncMock(return_value=True)
    mock_tab.first.click = AsyncMock()

    def side_effect(selector):
        if "balance" in selector:
            return mock_balance
        if "tabs" in selector or "text='Login'" in selector:
            return mock_tab
        return MagicMock()

    client.page.locator.side_effect = side_effect
    # Primary inputs wait fails, Tab switch happens, secondary inputs wait succeeds
    client.page.wait_for_selector = AsyncMock(side_effect=[Exception("Timeout"), None])
    client.page.wait_for_url = AsyncMock()

    with patch('asyncio.sleep', AsyncMock()):
        await client.login()

    # Verify tab switch was attempted after primary input wait failed
    mock_tab.first.click.assert_called()
