import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from main import main, update_learning_state

@pytest.mark.asyncio
@patch('main.validate_config', return_value=True)
@patch('main.ExnessClient')
@patch('main.DBClient')
@patch('main.Strategy')
@patch('main.Executor')
@patch('main.update_learning_state')
async def test_main_flow(mock_update, mock_executor_class, mock_strategy_class,
                         mock_db_class, mock_exness_class, mock_validate):

    mock_exness = mock_exness_class.return_value
    mock_exness.close = AsyncMock()
    mock_executor = mock_executor_class.return_value
    mock_executor.run_cycle = AsyncMock()
    await main()

    mock_validate.assert_called_once()
    mock_executor.run_cycle.assert_called_once()
    mock_update.assert_called_once()

@pytest.mark.asyncio
@patch('main.logger')
async def test_update_learning_state(mock_logger):
    from datetime import datetime, UTC
    exness = MagicMock()
    db = MagicMock()

    exness.get_account_summary = AsyncMock(return_value={"balance": 105.00})
    db.get_daily_trades.return_value = [
        {"instrument": "XAUUSD", "profit_loss": 10, "status": "CLOSED"},
        {"instrument": "GBPJPY", "profit_loss": -5, "status": "CLOSED"}
    ]
    db.get_latest_learning_state.return_value = {
        "initial_daily_balance": 100,
        "timestamp": datetime.now(UTC)
    }
    # Mock reconcile_trades to do nothing
    with patch('main.reconcile_trades', AsyncMock()):
        await update_learning_state(exness, db)

    db.save_learning_state.assert_called_once()
    state_data = db.save_learning_state.call_args[0][0]
    assert state_data["balance"] == 105.00
    assert state_data["daily_pnl"] == 5
