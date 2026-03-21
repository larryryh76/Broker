import os
import pymongo
from datetime import datetime, timezone
from typing import List, Dict, Optional

class MemoryGraph:
    def __init__(self, uri: str):
        self.client = pymongo.MongoClient(uri)
        self.db = self.client["omni_v35"]
        self.spins = self.db["spins"]
        self.sequences = self.db["sequences"]
        self.models = self.db["models"]
        self.sessions = self.db["sessions"]

    def log_spin(self, outcome: str):
        """outcome: 'U' (Up) or 'D' (Down)"""
        self.spins.insert_one({
            "outcome": outcome,
            "timestamp": datetime.now(timezone.utc)
        })

    def get_latest_spins(self, limit=50) -> List[str]:
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

    def get_sequence_node(self, sequence: str) -> Optional[Dict]:
        return self.sequences.find_one({"sequence": sequence})

    def save_session(self, state: Dict):
        state["last_sync"] = datetime.now(timezone.utc)
        self.sessions.update_one({"id": "current"}, {"$set": state}, upsert=True)

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
