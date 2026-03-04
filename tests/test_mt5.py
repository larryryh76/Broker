import pytest
from unittest.mock import MagicMock, patch
from mt5_client import MT5Client

@pytest.fixture
def mt5_client():
    with patch('mt5_client.MT5_LOGIN', 298682494), \
         patch('mt5_client.MT5_PASSWORD', 'Iamolanrewaju1$'), \
         patch('mt5_client.MT5_SERVER', 'FBS-Real'), \
         patch('os.path.exists', return_value=True), \
         patch('subprocess.Popen'), \
         patch('mt5_client.mt5') as mock_mt5:
        client = MT5Client()
        yield client, mock_mt5

def test_get_account_summary(mt5_client):
    client, mock_mt5 = mt5_client
    mock_mt5.initialize.return_value = True
    mock_mt5.account_info.return_value = MagicMock(balance=100.0, equity=100.0, currency="USD")

    summary = client.get_account_summary()
    assert summary["balance"] == 100.0
    mock_mt5.initialize.assert_called_once()

def test_get_candles(mt5_client):
    client, mock_mt5 = mt5_client
    mock_mt5.initialize.return_value = True
    mock_mt5.copy_rates_from_pos.return_value = [
        {'time': 1600000000, 'open': 100, 'high': 101, 'low': 99, 'close': 100, 'tick_volume': 10}
    ]

    candles = client.get_candles("XAUUSD")
    assert len(candles) == 1
    assert candles[0]["mid"]["o"] == "100"

def test_place_market_order(mt5_client):
    client, mock_mt5 = mt5_client
    mock_mt5.initialize.return_value = True
    mock_mt5.symbol_info_tick.return_value = MagicMock(ask=100, bid=99)
    mock_mt5.order_send.return_value = MagicMock(retcode=0, order=123)
    mock_mt5.TRADE_RETCODE_DONE = 0

    result = client.place_market_order("XAUUSD", 0.01, stop_loss=98, take_profit=106)
    assert result["orderFillTransaction"]["id"] == "123"
