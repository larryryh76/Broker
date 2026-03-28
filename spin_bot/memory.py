import os
import pymongo
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

class MemoryGraph:
    def __init__(self, uri: str):
        self.client = pymongo.MongoClient(uri)
        self.db = self.client["omni_v4"]

        self.spins = self.db["spins"]
        self.sequences = self.db["sequences"]
        self.models = self.db["models"]
        self.sessions = self.db["sessions"]
        self.selectors = self.db["selectors"]
        self.tokens = self.db["session_tokens"]
        self.cookies = self.db["cookies"] # V3.0 Cookie Persistence

    def log_spin(self, outcome: str, history_context: List[str] = None):
        """
        outcome: 'U' (Up), 'D' (Down), or 'M' (Middle).
        V5.10.1 Deterministic Pattern Deduplication (Pure 5-gram).
        """
        if not history_context:
            history_context = []

        # Use last 4 from context + current outcome = 5-gram pattern
        pattern = "".join(history_context[-4:]) + outcome

        # Pure deterministic hash of the 5-gram outcome sequence
        unique_id = hashlib.sha256(pattern.encode()).hexdigest()

        try:
            self.spins.update_one(
                {"unique_id": unique_id},
                {"$setOnInsert": {
                    "outcome": outcome,
                    "timestamp": datetime.now(timezone.utc),
                    "unique_id": unique_id,
                    "state": pattern
                }},
                upsert=True
            )
        except: pass

    def get_latest_spins(self, limit=200) -> List[str]:
        cursor = self.spins.find().sort("timestamp", -1).limit(limit)
        return [doc["outcome"] for doc in list(cursor)][::-1]

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

    # V3.0 Browser Persistence
    def save_cookies(self, cookie_data: List[Dict]):
        self.cookies.update_one(
            {"id": "active_session"},
            {"$set": {"data": cookie_data, "last_updated": datetime.now(timezone.utc)}},
            upsert=True
        )

    def load_cookies(self) -> Optional[List[Dict]]:
        doc = self.cookies.find_one({"id": "active_session"})
        return doc["data"] if doc else None

    def close(self):
        self.client.close()
