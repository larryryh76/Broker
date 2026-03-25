import os
import time
import json
import asyncio
import random
from typing import List, Dict, Optional, Any
from spin_bot.memory import MemoryGraph
from spin_bot.models import EnsembleBrain
from spin_bot.risk import RiskEngine
from spin_bot.executor import DecisionExecutor
from spin_bot.playwright_client import PlaywrightClient
from spin_bot.api_client import OmniAPIClient, normalize_url
from datetime import datetime, timezone

class OmniMachineV30Alpha:
    def __init__(self):
        # 1. Initialize MongoDB Persistence
        self.memory = MemoryGraph(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))

        # 2. Reconstruct System State
        self.session_state = self.memory.load_session() or {
            "bankroll": 300.0,
            "mode": "COLD_START",
            "peak_equity": 300.0,
            "vault_locked": False,
            "history": []
        }

        # 3. Model Weight Loading
        weights = self.memory.load_model_weights()
        self.brain = EnsembleBrain(weights)

        # 4. Risk Engine & Staking Logic
        self.risk = RiskEngine(self.session_state["bankroll"], self.session_state)

        # 5. Prediction Engine
        self.executor = DecisionExecutor(self.brain, self.risk)

    async def run_alpha_cycle(self):
        """V3.0 Alpha Execution Loop: Cold Start & Vault."""
        print(f"--- OMNI MACHINE CYCLE V3.0 ALPHA ({self.session_state['mode']}) ---")
        client = PlaywrightClient("https://www.football.com")

        try:
            await client.setup()
            await client.login()

            if not await client.enter_game_environment():
                print("CRITICAL: Failed to enter Game Environment.")
                return

            # PHASE 1: THE COLD START
            # IF DB is empty or in COLD_START mode, scrape history to build the brain
            history_needed = 100
            current_history = self.memory.get_latest_spins(history_needed)

            if len(current_history) < history_needed:
                print(f"COLD START: Scraping initial {history_needed} results...")
                scraped = await client.capture_history_texts()
                for s in scraped: self.memory.log_spin(s)
                current_history = self.memory.get_latest_spins(history_needed)

            # PHASE 3: ENSEMBLE BRAIN (Decision)
            probs = self.brain.predict(current_history)
            direction = "U" if probs["U"] > probs["D"] else "D"
            win_prob = probs[direction]
            confidence = abs(win_prob - 0.5) * 2.0

            print(f"STATE UPDATED: {len(current_history)} spins recorded. Confidence: {confidence*100:.1f}%")

            # Check Vault floor
            if self.risk.bankroll <= 500:
                print("VAULT PROTECTED: ₦500 Floor Reached. Observation mode ONLY.")
                # Force observation mode
                self.session_state["mode"] = "OBSERVATION_ONLY"
            elif confidence > 0.7:
                self.session_state["mode"] = "LIVE_BETTING"
            else:
                self.session_state["mode"] = "COLD_START"

            # Execution logic
            if self.session_state["mode"] == "LIVE_BETTING":
                decision = self.executor.decide(current_history)
                if decision["action"] == "BET" and decision["ev"] > 0.05:
                    print(f"EXECUTION: Bet ₦{decision['amount']} on {decision['direction']}")
                    success = await client.place_ui_bet(decision["direction"], decision["amount"])
                    if success:
                        await asyncio.sleep(15)
                        new_results = await client.capture_history_texts()
                        if new_results:
                            actual = new_results[-1]
                            win = (actual == decision["direction"])
                            print(f"RESULT: {'WIN' if win else 'LOSS'} (Outcome: {actual})")
                            self.brain.update_weights(current_history, actual)
                            payout = decision["amount"] * 1.95 if win else 0
                            self.risk.bankroll += (payout - decision["amount"])
                            self.risk.update_result(win)
                else:
                    print(f"SKIP: {decision.get('reason', 'Confidence/EV Threshold not met')}")
            else:
                print(f"MODE: {self.session_state['mode']}. Recording outcomes for Mental State...")
                scraped = await client.capture_history_texts()
                if scraped:
                    last_outcome = scraped[-1]
                    self.memory.log_spin(last_outcome)

            client.save_cycle_logs()

        except Exception as e:
            print(f"CRITICAL ERROR in V3.0 Cycle: {e}")
        finally:
            self.session_state["bankroll"] = self.risk.bankroll
            self.memory.save_session(self.session_state)
            self.memory.save_model_weights(self.brain.weights)
            await client.close()
            self.memory.close()
            print(f"--- CYCLE COMPLETE (Bankroll: ₦{self.risk.bankroll:.2f}) ---")

if __name__ == "__main__":
    machine = OmniMachineV30Alpha()
    asyncio.run(machine.run_alpha_cycle())
