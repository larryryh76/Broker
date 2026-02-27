import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from exness_client import ExnessClient

@pytest.fixture
def exness_client():
    with patch('exness_client.META_API_TOKEN', 'fake_token'), \
         patch('exness_client.META_API_ACCOUNT_ID', 'fake_id'), \
         patch('exness_client.MetaApi'):
        return ExnessClient()

@pytest.mark.asyncio
async def test_get_account_summary(exness_client):
    exness_client.connection = AsyncMock()
    exness_client.connection.get_account_information.return_value = {
        "balance": 100.0,
        "equity": 100.0,
        "currency": "USD"
    }

    summary = await exness_client.get_account_summary()
    assert summary["balance"] == 100.0
    exness_client.connection.get_account_information.assert_called_once()

@pytest.mark.asyncio
async def test_get_candles(exness_client):
    exness_client.connection = AsyncMock()
    exness_client.connection.get_historical_candles.return_value = [
        {"time": "2023-01-01T00:00:00Z", "open": 100, "high": 101, "low": 99, "close": 100, "tickVolume": 10}
    ]

    candles = await exness_client.get_candles("XAUUSD")
    assert len(candles) == 1
    assert candles[0]["mid"]["o"] == "100"

@pytest.mark.asyncio
async def test_place_market_order(exness_client):
    exness_client.connection = AsyncMock()
    exness_client.connection.create_market_buy_order.return_value = {"orderId": "123"}

    result = await exness_client.place_market_order("XAUUSD", 0.01, stop_loss=1900, take_profit=2000)
    assert result["orderFillTransaction"]["id"] == "123"
