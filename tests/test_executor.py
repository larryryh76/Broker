import pytest
from unittest.mock import MagicMock, patch
from executor import Executor

@pytest.fixture
def executor():
    oanda = MagicMock()
    db = MagicMock()
    strategy = MagicMock()
    return Executor(oanda, db, strategy)

def test_check_circuit_breaker_active(executor):
    from datetime import datetime, UTC
    executor.db.get_latest_learning_state.return_value = {
        "initial_daily_balance": 100,
        "timestamp": datetime.now(UTC)
    }
    # 6% drawdown
    assert executor.check_circuit_breaker(94) is True

def test_check_circuit_breaker_inactive(executor):
    from datetime import datetime, UTC
    executor.db.get_latest_learning_state.return_value = {
        "initial_daily_balance": 100,
        "timestamp": datetime.now(UTC)
    }
    # 4% drawdown
    assert executor.check_circuit_breaker(96) is False

@patch('time.sleep', return_value=None)
@patch('executor.random.randint', return_value=1)
def test_execute_signal(mock_rand, mock_sleep, executor):
    executor.strategy.calculate_levels.return_value = (98, 106)
    executor.strategy.calculate_position_size.return_value = 1
    executor.oanda.get_current_price.return_value = 100
    executor.oanda.place_market_order.return_value = {"orderFillTransaction": {"id": "123"}}

    signal = {"instrument": "XAU_USD", "side": "BUY", "price": 100, "confidence": 0.95}
    executor.execute_signal(signal, 100)

    executor.oanda.place_market_order.assert_called_once()
    executor.db.log_trade.assert_called_once()
