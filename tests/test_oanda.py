import pytest
from unittest.mock import MagicMock, patch
from oanda_client import OandaClient

@pytest.fixture
def oanda_client():
    with patch('oanda_client.OANDA_TOKEN', 'fake_token'), \
         patch('oanda_client.OANDA_ACCOUNT_ID', 'fake_id'):
        return OandaClient()

@patch('requests.get')
def test_get_account_summary(mock_get, oanda_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {"account": {"balance": "100.00"}}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    summary = oanda_client.get_account_summary()
    assert summary["balance"] == "100.00"
    mock_get.assert_called_once()

@patch('requests.get')
def test_get_candles(mock_get, oanda_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {"candles": [{"time": "2023-01-01T00:00:00Z"}]}
    mock_response.raise_for_status.return_value = None
    mock_get.return_value = mock_response

    candles = oanda_client.get_candles("XAU_USD")
    assert len(candles) == 1
    assert candles[0]["time"] == "2023-01-01T00:00:00Z"

@patch('requests.post')
def test_place_market_order(mock_post, oanda_client):
    mock_response = MagicMock()
    mock_response.json.return_value = {"orderFillTransaction": {"id": "123"}}
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    result = oanda_client.place_market_order("XAU_USD", 1, stop_loss=98, take_profit=106)
    assert result["orderFillTransaction"]["id"] == "123"
    mock_post.assert_called_once()
