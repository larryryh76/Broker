import os
from pymongo import MongoClient
from datetime import datetime, timezone
import config

class DBClient:
    def __init__(self):
        self.uri = os.getenv("MONGODB_URI")
        self.client = MongoClient(self.uri) if self.uri else None
        self.db = self.client["money_machine"] if self.client else None
        self.state_collection = self.db["learning_state"] if self.db else None
        self.trades_collection = self.db["trades"] if self.db else None

    def get_latest_state(self):
        if self.state_collection is None:
            return None
        return self.state_collection.find_one(sort=[("timestamp", -1)])

    def save_state(self, state_data):
        if self.state_collection is None:
            return
        state_data["timestamp"] = datetime.now(timezone.utc)
        self.state_collection.insert_one(state_data)

    def log_trade(self, trade_data):
        if self.trades_collection is None:
            return
        trade_data["timestamp"] = datetime.now(timezone.utc)
        self.trades_collection.insert_one(trade_data)

    def get_total_realized_profit(self):
        if self.trades_collection is None:
            return 0.0
        pipeline = [
            {"$group": {"_id": None, "total": {"$sum": "$profit_loss"}}}
        ]
        result = list(self.trades_collection.aggregate(pipeline))
        return result[0]["total"] if result else 0.0
