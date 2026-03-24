import os
import time
import json
from typing import List, Dict, Optional, Any
from spin_bot.memory import MemoryGraph
from spin_bot.models import EnsembleBrain
from spin_bot.risk import RiskEngine
from spin_bot.executor import DecisionExecutor
from spin_bot.playwright_client import PlaywrightClient
from spin_bot.api_client import OmniAPIClient
from datetime import datetime, timezone

class OmniMachineV51:
    def __init__(self):
        # 1. Initialize MongoDB Persistence
        self.memory = MemoryGraph(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))

        # 2. Reconstruct System State
        self.session_state = self.memory.load_session() or {
            "bankroll": 300.0,
            "mode": "TUITION",
            "tuition_spins": 0,
            "peak_equity": 300.0,
            "consecutive_losses": 0,
            "vault_locked": False,
            "history": [],
            "selectors": {}
        }

        # 3. Model Weight Loading
        weights = self.memory.load_model_weights()
        self.brain = EnsembleBrain(weights)

        # 4. Risk Engine & Staking Logic
        self.risk = RiskEngine(self.session_state["bankroll"], self.session_state)

        # 5. Prediction Engine
        self.executor = DecisionExecutor(self.brain, self.risk)

        # 6. API Client (V5.1 Primary Path)
        self.api_client = OmniAPIClient()

    def _refresh_session(self):
        """V5.1 Fallback to Browser for Forced Discovery."""
        print("DEBUG: Refreshing Session via Forced Discovery (V5.1)...")
        client = PlaywrightClient(os.getenv("SPIN_URL", "https://football.com/ng/games/spin"))
        try:
            client.navigate_to_spin_game()
            client.save_network_logs()

            # Extract session data from logs
            with open("artifacts/network_log.json", "r") as f:
                logs = json.load(f)

            # Find a valid authenticated request
            auth_data = {}
            for entry in reversed(logs):
                if entry["type"] == "REQUEST":
                    headers = entry.get("headers", {})
                    if "authorization" in headers or "cookie" in headers:
                        auth_data = {
                            "headers": headers,
                            "cookies": entry.get("cookies", []),
                            "endpoints": client.endpoints
                        }
                        break

            if auth_data:
                self.memory.save_session_tokens(auth_data)
                self.api_client.apply_session(auth_data)
                print(f"DEBUG: V5.1 Session refreshed. Endpoints Found: {client.endpoints}")
            else:
                print("CRITICAL: Failed to discover auth data in network logs.")
        finally:
            client.close()

    def run_cycle(self):
        print(f"--- STARTING OMNI MACHINE CYCLE V5.1 (FORCED DISCOVERY) ---")

        try:
            # 1. Load Session Tokens
            tokens = self.memory.load_session_tokens()
            if not tokens:
                self._refresh_session()
                tokens = self.memory.load_session_tokens()

            if tokens:
                self.api_client.apply_session(tokens)
            else:
                print("CRITICAL: No valid session tokens available. Aborting.")
                return

            # 2. API-Based Observation
            outcomes = self.api_client.get_spin_history()

            # Fallback if history endpoint is missing or returns 403
            if not outcomes:
                print("DEBUG: API fetch failed or history endpoint missing. Refreshing...")
                self._refresh_session()
                outcomes = self.api_client.get_spin_history()

            # 3. Prediction & Execution Phase
            if outcomes:
                print(f"Observed Intelligence (API): {''.join(outcomes[:10])}...")
                for o in outcomes: self.memory.log_spin(o)

                full_history = self.memory.get_latest_spins(100)
                decision = self.executor.decide(full_history)

                if decision["action"] == "BET":
                    print(f"Executing Bet via API: ₦{decision['amount']} on {decision['direction']}")
                    result = self.api_client.place_bet(decision["direction"], decision["amount"])

                    if "error" not in result:
                        print(f"API Bet Success: {result}")
                        actual = result.get("outcome", outcomes[0])
                        win = (actual == decision["direction"])
                        self.brain.update_weights(full_history, actual)
                        payout = decision["amount"] * 1.95 if win else 0
                        self.risk.bankroll += (payout - decision["amount"])
                        self.risk.update_result(win)
                    else:
                        print(f"API Bet FAILED: {result}")
                else:
                    print(f"SKIP: {decision['reason']}")
            else:
                print("CRITICAL: API Observation FAILED even after refresh.")

        except Exception as e:
            print(f"CRITICAL ERROR in V5.1 Cycle: {e}")
        finally:
            # 4. Permanent Persistence Phase
            self.session_state["bankroll"] = self.risk.bankroll
            self.memory.save_session(self.session_state)
            self.memory.save_model_weights(self.brain.weights)
            self.memory.close()
            print(f"--- CYCLE COMPLETE (Bankroll: ₦{self.risk.bankroll:.2f}) ---")

if __name__ == "__main__":
    machine = OmniMachineV51()
    machine.run_cycle()
