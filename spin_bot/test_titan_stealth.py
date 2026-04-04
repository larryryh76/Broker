import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from spin_bot.titan_stealth import TitanStealthClient

@pytest.mark.asyncio
async def test_force_clear_overlays_injection():
    client = TitanStealthClient()
    client.page = AsyncMock()

    await client._force_clear_overlays()

    # Verify evaluate was called with the selector removal script
    client.page.evaluate.assert_called()
    args, kwargs = client.page.evaluate.call_args
    script = args[0]
    assert ".dialog-mask" in script
    assert "el.remove()" in script

@pytest.mark.asyncio
async def test_handle_region_trap_fallback():
    client = TitanStealthClient()
    client.page = MagicMock()
    client._force_clear_overlays = AsyncMock()

    # Mock locator to fail (timeout)
    mock_nigeria = MagicMock()
    mock_nigeria.wait_for = AsyncMock(side_effect=Exception("Timeout"))
    client.page.locator.return_value.filter.return_value = mock_nigeria

    await client.handle_region_trap()

    # Verify fallback to nuclear option
    client._force_clear_overlays.assert_called()

@pytest.mark.asyncio
async def test_human_type_force_click():
    client = TitanStealthClient()
    client.page = MagicMock()
    mock_target = MagicMock()
    mock_target.first = MagicMock()
    mock_target.first.click = AsyncMock()
    client.page.locator.return_value = mock_target
    client.page.keyboard = AsyncMock()

    with patch('asyncio.sleep', AsyncMock()):
        await client.human_type("#selector", "1")

    # Verify force=True was used
    mock_target.first.click.assert_called_with(force=True)
