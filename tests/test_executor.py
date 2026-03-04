import pytest
from unittest.mock import MagicMock, patch
from executor import Executor

@pytest.fixture
def executor():
    mt5 = MagicMock()
    db = MagicMock()
    strategy = MagicMock()
    return Executor(mt5, db, strategy)

def test_check_circuit_breaker_active(executor):
    from datetime import datetime, timezone
    executor.db.get_latest_learning_state.return_value = {
        "initial_daily_virtual_equity": 100,
        "timestamp": datetime.now(timezone.utc)
    }
    assert executor.check_circuit_breaker(94) is True

@patch('time.sleep', return_value=None)
@patch('executor.random.randint', return_value=1)
@patch('executor.mt5_lib', create=True)
def test_execute_signal(mock_mt5_lib, mock_rand, mock_sleep, executor):
    executor.strategy.calculate_levels.return_value = (98, 106)
    executor.strategy.calculate_position_size.return_value = 0.01
    executor.mt5.symbol_info.return_value = MagicMock(point=0.01)
    executor.mt5.symbol_info_tick.return_value = MagicMock(ask=100.1, bid=100.0)
    executor.mt5.get_current_price.return_value = 100
    executor.mt5.place_market_order.return_value = {"orderFillTransaction": {"id": "123"}}

    signal = {"instrument": "XAUUSD", "side": "BUY", "price": 100, "confidence": 0.95}
    executor.execute_signal(signal, 100)

    executor.mt5.place_market_order.assert_called_once()
    executor.db.log_trade.assert_called_once()
