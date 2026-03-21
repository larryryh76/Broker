import os
import time
from typing import List, Dict, Optional
from spin_bot.memory import MemoryGraph
from spin_bot.models import EnsembleBrain
from spin_bot.risk import RiskEngine
from spin_bot.executor import DecisionExecutor
from spin_bot.playwright_client import PlaywrightClient
from datetime import datetime, timezone

class OmniMachineV35:
    def __init__(self):
        # 1. Initialize MongoDB Intelligence Layer
        self.memory = MemoryGraph(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))

        # 2. Reconstruct State (Load Session)
        self.session_state = self.memory.load_session() or {
            "bankroll": 300.0,
            "mode": "TUITION",
            "tuition_spins": 0,
            "peak_equity": 300.0,
            "consecutive_losses": 0,
            "vault_locked": False,
            "history": []
        }

        # 3. Initialize Model weights
        weights = self.memory.load_model_weights()
        self.brain = EnsembleBrain(weights)

        # 4. Financial engine & Risk Layer
        self.risk = RiskEngine(self.session_state["bankroll"], self.session_state)

        # 5. Prediction orchestrator
        self.executor = DecisionExecutor(self.brain, self.risk)

    def run_cycle(self):
        print(f"--- STARTING OMNI MACHINE CYCLE ({self.session_state['mode']}) ---")

        # 1. Observation Phase (Scrape recent history)
        client = PlaywrightClient(os.getenv("SPIN_URL", "https://football.com/ng/games/spin"))
        try:
            client.navigate_to_spin_game()
            outcomes = client.get_latest_outcomes()

            # Synchronize history
            if outcomes:
                print(f"Observed: {''.join(outcomes)}")
                for outcome in outcomes:
                    self.memory.log_spin(outcome)

            # Fetch full history from DB
            full_history = self.memory.get_latest_spins(50)

            # 2. Intelligence Phase (Update models and calculate edge)
            decision = self.executor.decide(full_history)

            if decision["action"] == "BET":
                print(f"Decision: BET ₦{decision['amount']} on {decision['direction']} (EV: {decision['ev']:.2f})")

                # Execute Bet via Browser
                client.place_bet(decision["amount"], decision["direction"])

                # 3. Adaptation Phase (Monitor result and update models)
                # Wait for next spin to get the outcome
                time.sleep(15)
                new_outcomes = client.get_latest_outcomes()
                if new_outcomes:
                    actual = new_outcomes[-1]
                    win = (actual == decision["direction"])
                    print(f"RESULT: {'WIN' if win else 'LOSS'} (Outcome: {actual})")

                    # Update Memory Graph Patterns
                    if len(full_history) >= 5:
                        seq = "".join(full_history[-5:])
                        self.memory.update_sequence(seq, actual, win)

                    # Update AI Weights
                    self.brain.update_weights(full_history, actual)

                    # Update Financial State
                    payout = decision["amount"] * 1.95 if win else 0
                    self.risk.bankroll += (payout - decision["amount"])
                    self.risk.update_result(win)
            else:
                print(f"Decision: WAIT ({decision['reason']})")

        finally:
            # 4. Persistent Phase (Save State)
            self.session_state["bankroll"] = self.risk.bankroll
            self.memory.save_session(self.session_state)
            self.memory.save_model_weights(self.brain.weights)
            client.close()
            print(f"--- CYCLE COMPLETE (Bankroll: ₦{self.risk.bankroll:.2f}) ---")

if __name__ == "__main__":
    machine = OmniMachineV35()
    machine.run_cycle()
