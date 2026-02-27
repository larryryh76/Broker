import pytest
from unittest.mock import MagicMock, patch
from db_client import DBClient

@pytest.fixture
def db_client():
    with patch('db_client.MongoClient') as mock_mongo:
        mock_db = MagicMock()
        mock_mongo.return_value.__getitem__.return_value = mock_db
        return DBClient()

def test_log_trade(db_client):
    db_client.trades_collection = MagicMock()
    db_client.trades_collection.insert_one.return_value.inserted_id = "abc"

    trade_id = db_client.log_trade({"instrument": "XAU_USD", "profit_loss": 10})
    assert trade_id == "abc"
    db_client.trades_collection.insert_one.assert_called_once()

def test_get_latest_learning_state(db_client):
    db_client.learning_state_collection = MagicMock()
    db_client.learning_state_collection.find_one.return_value = {"balance": 100}

    state = db_client.get_latest_learning_state()
    assert state["balance"] == 100
    db_client.learning_state_collection.find_one.assert_called_once()
