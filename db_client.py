from pymongo import MongoClient
from datetime import datetime
from config import MONGODB_URI, DB_NAME, logger

class DBClient:
    def __init__(self):
        try:
            self.client = MongoClient(MONGODB_URI)
            self.db = self.client[DB_NAME]
            self.trades_collection = self.db["trades"]
            self.learning_state_collection = self.db["learning_state"]
        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            raise

    def log_trade(self, trade_data):
        """
        trade_data: dict with entry_price, exit_price, lot_size, profit_loss,
        confidence, instrument, entry_time, exit_time, etc.
        """
        try:
            trade_data["timestamp"] = datetime.utcnow()
            # Mark as open if not specified
            if "status" not in trade_data:
                trade_data["status"] = "OPEN"
            result = self.trades_collection.insert_one(trade_data)
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error logging trade to MongoDB: {e}")
            return None

    def update_trade(self, order_id, update_data):
        try:
            self.trades_collection.update_one(
                {"order_id": str(order_id)},
                {"$set": update_data}
            )
        except Exception as e:
            logger.error(f"Error updating trade {order_id}: {e}")

    def get_open_logged_trades(self):
        try:
            return list(self.trades_collection.find({"status": "OPEN"}))
        except Exception as e:
            logger.error(f"Error fetching open logged trades: {e}")
            return []

    def get_latest_learning_state(self):
        try:
            return self.learning_state_collection.find_one(sort=[("timestamp", -1)])
        except Exception as e:
            logger.error(f"Error fetching latest learning state: {e}")
            return None

    def save_learning_state(self, state_data):
        """
        state_data: dict with balance, daily_pnl, total_trades, win_rate,
        max_drawdown, instrument_performance, etc.
        """
        try:
            state_data["timestamp"] = datetime.utcnow()
            result = self.learning_state_collection.insert_one(state_data)
            return result.inserted_id
        except Exception as e:
            logger.error(f"Error saving learning state to MongoDB: {e}")
            return None

    def get_daily_trades(self):
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
        try:
            return list(self.trades_collection.find({"timestamp": {"$gte": today}}))
        except Exception as e:
            logger.error(f"Error fetching daily trades: {e}")
            return []

    def clear_learning_state(self):
        try:
            self.learning_state_collection.delete_many({})
            logger.info("Cleared learning state (Hard Reset).")
        except Exception as e:
            logger.error(f"Error clearing learning state: {e}")
