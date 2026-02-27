import pytest
from unittest.mock import MagicMock, patch
from main import main, update_learning_state

@patch('main.validate_config', return_value=True)
@patch('main.OandaClient')
@patch('main.DBClient')
@patch('main.Strategy')
@patch('main.Executor')
@patch('main.update_learning_state')
def test_main_flow(mock_update, mock_executor_class, mock_strategy_class,
                   mock_db_class, mock_oanda_class, mock_validate):

    mock_executor = mock_executor_class.return_value
    main()

    mock_validate.assert_called_once()
    mock_executor.run_cycle.assert_called_once()
    mock_update.assert_called_once()

@patch('main.logger')
def test_update_learning_state(mock_logger):
    from datetime import datetime, UTC
    oanda = MagicMock()
    db = MagicMock()

    oanda.get_account_summary.return_value = {"balance": "105.00"}
    db.get_daily_trades.return_value = [
        {"instrument": "XAU_USD", "profit_loss": 10, "status": "CLOSED"},
        {"instrument": "GBP_JPY", "profit_loss": -5, "status": "CLOSED"}
    ]
    db.get_latest_learning_state.return_value = {
        "initial_daily_balance": 100,
        "timestamp": datetime.now(UTC)
    }

    update_learning_state(oanda, db)

    db.save_learning_state.assert_called_once()
    state_data = db.save_learning_state.call_args[0][0]
    assert state_data["balance"] == 105.00
    assert state_data["daily_pnl"] == 5
    assert state_data["win_rate"] == 50.0
    assert state_data["total_trades"] == 2
