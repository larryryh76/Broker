import os
import pymongo
from datetime import datetime, timezone
from typing import List, Dict, Optional

class MemoryGraph:
    def __init__(self, uri: str):
        # 1. Connect to MongoDB Atlas
        self.client = pymongo.MongoClient(uri)
        self.db = self.client["omni_v4"]

        # 2. Collection definitions
        self.spins = self.db["spins"]           # Raw spin outcomes
        self.sequences = self.db["sequences"]   # Pattern intelligence nodes
        self.models = self.db["models"]         # Ensemble model weights and performance
        self.sessions = self.db["sessions"]     # Global bankroll and system state
        self.selectors = self.db["selectors"]   # Self-healed CSS selectors

    def log_spin(self, outcome: str):
        """outcome: 'U' (Up) or 'D' (Down)"""
        self.spins.insert_one({
            "outcome": outcome,
            "timestamp": datetime.now(timezone.utc)
        })

    def get_latest_spins(self, limit=100) -> List[str]:
        cursor = self.spins.find().sort("timestamp", -1).limit(limit)
        return [doc["outcome"] for doc in list(cursor)][::-1]

    def update_sequence(self, sequence: str, next_outcome: str, win: bool):
        """Update intelligence for a specific sequence pattern."""
        update = {
            "$inc": {
                "occurrences": 1,
                "wins": 1 if win else 0,
                "losses": 0 if win else 1
            },
            "$set": {
                "last_updated": datetime.now(timezone.utc)
            }
        }
        self.sequences.update_one({"sequence": sequence}, update, upsert=True)

    def save_session(self, state: Dict):
        state["last_sync"] = datetime.now(timezone.utc)
        self.sessions.update_one({"id": "current"}, {"$set": state}, upsert=True)
        print(f"Session state saved: ₦{state['bankroll']:.2f} | Mode: {state['mode']}")

    def load_session(self) -> Optional[Dict]:
        return self.sessions.find_one({"id": "current"})

    def save_model_weights(self, weights: Dict):
        self.models.update_one(
            {"id": "ensemble"},
            {"$set": {"weights": weights, "last_updated": datetime.now(timezone.utc)}},
            upsert=True
        )

    def load_model_weights(self) -> Optional[Dict]:
        doc = self.models.find_one({"id": "ensemble"})
        return doc["weights"] if doc else None

    def save_selector(self, key: str, value: str):
        self.selectors.update_one(
            {"key": key},
            {"$set": {"selector": value, "last_detected": datetime.now(timezone.utc)}},
            upsert=True
        )

    def get_selector(self, key: str) -> Optional[str]:
        doc = self.selectors.find_one({"key": key})
        return doc["selector"] if doc else None

    def close(self):
        self.client.close()
