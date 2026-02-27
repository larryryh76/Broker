import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from executor import Executor

@pytest.fixture
def executor():
    exness = MagicMock()
    db = MagicMock()
    strategy = MagicMock()
    return Executor(exness, db, strategy)

def test_check_circuit_breaker_active(executor):
    from datetime import datetime, UTC
    executor.db.get_latest_learning_state.return_value = {
        "initial_daily_balance": 100,
        "timestamp": datetime.now(UTC)
    }
    assert executor.check_circuit_breaker(94) is True

@pytest.mark.asyncio
@patch('asyncio.sleep', return_value=None)
@patch('executor.random.randint', return_value=1)
async def test_execute_signal(mock_rand, mock_sleep, executor):
    executor.strategy.calculate_levels.return_value = (98, 106)
    executor.strategy.calculate_position_size.return_value = 0.01
    executor.exness.get_current_price = AsyncMock(return_value=100)
    executor.exness.place_market_order = AsyncMock(return_value={"orderFillTransaction": {"id": "123"}})

    signal = {"instrument": "XAUUSD", "side": "BUY", "price": 100, "confidence": 0.95}
    await executor.execute_signal(signal, 100)

    executor.exness.place_market_order.assert_called_once()
    executor.db.log_trade.assert_called_once()
