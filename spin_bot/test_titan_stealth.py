import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from spin_bot.titan_stealth import TitanStealthClient

@pytest.mark.asyncio
async def test_handle_region_trap_logic():
    client = TitanStealthClient()
    client.page = MagicMock()

    # Mock finding the modal
    mock_modal = MagicMock()
    mock_modal.first = MagicMock()
    mock_modal.first.is_visible = AsyncMock(return_value=True)
    client.page.locator.return_value = mock_modal

    # Mock finding the Nigeria item
    mock_nigeria = MagicMock()
    mock_nigeria.first = MagicMock()
    mock_nigeria.first.wait_for = AsyncMock()
    mock_nigeria.first.click = AsyncMock()

    # Set up the locator to return the modal or nigeria item based on selector
    def side_effect(selector):
        if "location_preference" in selector:
            return mock_modal
        else:
            m = MagicMock()
            m.filter.return_value = mock_nigeria
            return m

    client.page.locator.side_effect = side_effect

    with patch('asyncio.sleep', AsyncMock()):
        await client.handle_region_trap()

    # Verify interaction with Nigeria item
    mock_nigeria.first.click.assert_called()

@pytest.mark.asyncio
async def test_human_type_simulation():
    client = TitanStealthClient()
    client.page = MagicMock()
    mock_target = MagicMock()
    mock_target.first = MagicMock()
    mock_target.first.click = AsyncMock()
    client.page.locator.return_value = mock_target
    client.page.keyboard = AsyncMock()

    test_text = "123"
    with patch('asyncio.sleep', AsyncMock()):
        await client.human_type("#selector", test_text)

    # Verify each character was typed
    assert client.page.keyboard.type.call_count == len(test_text)
