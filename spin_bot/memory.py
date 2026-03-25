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

    def log_spin(self, outcome: str, unique_key: Optional[str] = None):
        """
        outcome: 'U' (Up), 'D' (Down), or 'M' (Middle).
        V5.8 Refined Deduplication: Uses unique_key to prevent historical duplicates.
        """
        # If no key, fall back to timestamp-based hash (limited protection)
        key = unique_key or f"{outcome}-{datetime.now(timezone.utc).strftime('%Y-%m-%d-%H-%M')}"
        unique_id = hashlib.md5(key.encode()).hexdigest()

        try:
            self.spins.update_one(
                {"unique_id": unique_id},
                {"$setOnInsert": {
                    "outcome": outcome,
                    "timestamp": datetime.now(timezone.utc),
                    "unique_id": unique_id
                }},
                upsert=True
            )
        except: pass

    def get_latest_spins(self, limit=100) -> List[str]:
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

    def save_session_tokens(self, tokens: Dict[str, Any]):
        tokens["last_updated"] = datetime.now(timezone.utc)
        self.tokens.update_one({"id": "active_session"}, {"$set": tokens}, upsert=True)

    def load_session_tokens(self) -> Optional[Dict[str, Any]]:
        return self.tokens.find_one({"id": "active_session"})

    def close(self):
        self.client.close()
