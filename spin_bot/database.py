import os
import json
import time
import hashlib
import pymongo
from datetime import datetime, timezone
from typing import Optional, Dict, Any, List

class TitanDatabase:
    def __init__(self, uri: Optional[str] = None):
        self.mongodb_uri = uri or os.getenv("MONGODB_URI")
        self.db_client = None
        self.db = None
        self.sessions = None
        self.spins = None
        self.models = None
        self.setup()

    def setup(self):
        if not self.mongodb_uri:
            print("WARNING: MONGODB_URI not set. Persistence disabled.")
            return
        try:
            self.db_client = pymongo.MongoClient(self.mongodb_uri)
            self.db = self.db_client["omni_v4"]
            self.sessions = self.db["sessions"]
            self.spins = self.db["spins"]
            self.models = self.db["models"]
            print("DEBUG: MongoDB connected.")
        except Exception as e:
            print(f"ERROR: MongoDB connection failed: {e}")

    def load_storage_state(self) -> Optional[Dict[str, Any]]:
        if self.sessions is None: return None
        try:
            doc = self.sessions.find_one({"id": "titan_auth"})
            return doc.get("state") if doc else None
        except: return None

    def save_storage_state(self, state: Dict[str, Any]):
        if self.sessions is None: return
        try:
            self.sessions.update_one(
                {"id": "titan_auth"},
                {"$set": {"state": state, "updated_at": time.time()}},
                upsert=True
            )
        except Exception as e:
            print(f"ERROR: Failed to save storage_state: {e}")

    def log_spin(self, outcome: str, history_context: List[str] = None):
        if self.spins is None: return
        if not history_context: history_context = []
        pattern = "".join(history_context[-4:]) + outcome
        if len(pattern) < 5: return
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
        if self.spins is None: return []
        cursor = self.spins.find().sort("timestamp", -1).limit(limit)
        return [doc["outcome"] for doc in list(cursor)][::-1]

    def save_bot_session(self, state: Dict):
        if self.sessions is None: return
        state["last_sync"] = datetime.now(timezone.utc)
        self.sessions.update_one({"id": "current"}, {"$set": state}, upsert=True)

    def load_bot_session(self) -> Optional[Dict]:
        if self.sessions is None: return None
        return self.sessions.find_one({"id": "current"})

    def save_model_weights(self, weights: Dict):
        if self.models is None: return
        self.models.update_one(
            {"id": "ensemble"},
            {"$set": {"weights": weights, "last_updated": datetime.now(timezone.utc)}},
            upsert=True
        )

    def load_model_weights(self) -> Optional[Dict]:
        if self.models is None: return None
        doc = self.models.find_one({"id": "ensemble"})
        return doc["weights"] if doc else None

    def close(self):
        if self.db_client: self.db_client.close()
