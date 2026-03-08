import os
import bson
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
        self.models_collection = self.db["models"] if self.db else None

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

    def save_model(self, model_name, model_bytes):
        if self.models_collection is None:
            return
        self.models_collection.update_one(
            {"name": model_name},
            {"$set": {"data": bson.Binary(model_bytes), "timestamp": datetime.now(timezone.utc)}},
            upsert=True
        )

    def load_model(self, model_name):
        if self.models_collection is None:
            return None
        doc = self.models_collection.find_one({"name": model_name})
        return doc["data"] if doc else None
