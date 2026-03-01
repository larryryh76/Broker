import pytest
from unittest.mock import MagicMock, patch
from main import main, update_learning_state

@patch('main.validate_config', return_value=True)
@patch('main.MT5Client')
@patch('main.DBClient')
@patch('main.Strategy')
@patch('main.Executor')
@patch('main.update_learning_state')
@patch('main.update_day_and_get_target', return_value=50.0)
@patch('time.time', side_effect=[0, 0, 300]) # Force loop to run once
def test_main_flow(mock_time, mock_target, mock_update, mock_executor_class, mock_strategy_class,
                   mock_db_class, mock_mt5_class, mock_validate):

    mock_mt5 = mock_mt5_class.return_value
    mock_executor = mock_executor_class.return_value
    main()

    mock_validate.assert_called_once()
    mock_executor.run_cycle.assert_called_once()
    mock_update.assert_called_once()
    mock_mt5.close.assert_called_once()

@patch('main.logger')
def test_update_learning_state(mock_logger):
    from datetime import datetime, timezone
    mt5 = MagicMock()
    db = MagicMock()

    mt5.get_account_summary.return_value = {"balance": 105.00}
    db.get_daily_trades.return_value = [
        {"instrument": "XAUUSD", "profit_loss": 10, "status": "CLOSED"},
        {"instrument": "GBPJPY", "profit_loss": -5, "status": "CLOSED"}
    ]
    db.get_latest_learning_state.return_value = {
        "initial_daily_balance": 100,
        "timestamp": datetime.now(timezone.utc)
    }
    # Mock reconcile_trades to do nothing
    with patch('main.reconcile_trades'):
        update_learning_state(mt5, db)

    db.save_learning_state.assert_called_once()
    state_data = db.save_learning_state.call_args[0][0]
    assert state_data["balance"] == 105.00
    assert state_data["daily_pnl"] == 5
