import os
import pymongo
import hashlib
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

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
        self.tokens = self.db["session_tokens"] # V5.0 API Session Metadata

    def log_spin(self, outcome: str, timestamp: Optional[datetime] = None):
        """outcome: 'U' (Up) or 'D' (Down). V5.2 Includes deduplication."""
        ts = timestamp or datetime.now(timezone.utc)

        # Generate a deterministic hash for deduplication
        # Use outcome + timestamp to ensure we don't duplicate the same result
        unique_id = hashlib.md5(f"{outcome}-{ts.isoformat()}".encode()).hexdigest()

        try:
            self.spins.update_one(
                {"unique_id": unique_id},
                {"$setOnInsert": {
                    "outcome": outcome,
                    "timestamp": ts,
                    "unique_id": unique_id
                }},
                upsert=True
            )
        except: pass

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

    # V5.0 Session Token Management
    def save_session_tokens(self, tokens: Dict[str, Any]):
        """Persists API session metadata (headers, cookies)."""
        tokens["last_updated"] = datetime.now(timezone.utc)
        self.tokens.update_one({"id": "active_session"}, {"$set": tokens}, upsert=True)
        print("DEBUG: API Session tokens persisted to MongoDB.")

    def load_session_tokens(self) -> Optional[Dict[str, Any]]:
        """Loads API session metadata from MongoDB."""
        return self.tokens.find_one({"id": "active_session"})

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
