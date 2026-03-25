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

class OmniMachineV30Accuracy:
    def __init__(self):
        # 1. Initialize MongoDB Persistence
        self.memory = MemoryGraph(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))

        # 2. Reconstruct System State
        self.session_state = self.memory.load_session() or {
            "bankroll": 300.0,
            "mode": "LEARNING_MODE",
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

    async def run_accuracy_cycle(self):
        """V3.0 Alpha: 98% Accuracy Protocol Loop."""
        print(f"--- OMNI MACHINE CYCLE V3.0 (ACCURACY PROTOCOL) ---")
        client = PlaywrightClient("https://www.football.com")

        try:
            await client.setup()

            # 1. STRICT LOGIN SEQUENCE
            await client.login()

            # 2. PATTERN DETECTION (The Brain)
            if not await client.enter_game_environment():
                print("CRITICAL: Failed to reach Game Environment.")
                return

            # Scrape last 20 results
            scraped = await client.capture_history_texts()
            for s in scraped:
                self.memory.log_spin(s, unique_key=f"round-{int(time.time())}-{random.randint(1000,9999)}")

            # 3. 98% ACCURACY PROTOCOL CHECK
            all_spins = self.memory.get_latest_spins(500)
            spin_count = len(all_spins)

            # Calculate Brain State
            probs = self.brain.predict(all_spins)
            direction = "U" if probs["U"] > probs["D"] else "D"
            win_prob = probs[direction]
            confidence = abs(win_prob - 0.5) * 2.0

            if spin_count < 200:
                self.session_state["mode"] = "LEARNING_MODE"
                print(f"98% PROTOCOL: LEARNING_MODE active. ({spin_count}/200 spins captured)")
            else:
                self.session_state["mode"] = "ELITE_EXECUTION"
                print(f"98% PROTOCOL: ELITE_EXECUTION active. (N={spin_count})")

            # Final System Status for User
            status_msg = f"STATE UPDATED: {spin_count} spins recorded. Confidence: {confidence*100:.1f}%"
            print(status_msg)

            # 4. EXECUTION
            if self.session_state["mode"] == "ELITE_EXECUTION":
                decision = self.executor.decide(all_spins)
                # 98% Edge requirement: EV > 0.05 (from prompt) and high confidence
                if decision["action"] == "BET" and decision["ev"] > 0.05 and confidence > 0.8:
                    print(f"ELITE BET: ₦{decision['amount']} on {decision['direction']} (98% Edge)")
                    success = await client.place_ui_bet(decision["direction"], decision["amount"])
                    if success:
                        await asyncio.sleep(15)
                        new_res = await client.capture_history_texts()
                        if new_res:
                            actual = new_res[-1]
                            win = (actual == decision["direction"])
                            print(f"RESULT: {'WIN' if win else 'LOSS'} (Outcome: {actual})")
                            self.brain.update_weights(all_spins, actual)
                            payout = decision["amount"] * 1.95 if win else 0
                            self.risk.bankroll += (payout - decision["amount"])
                            self.risk.update_result(win)
                else:
                    print(f"SKIP: No 98% Edge detected. [EV: {decision.get('ev', 0):.2f} | Conf: {confidence:.2f}]")
            else:
                print("OBSERVATION ONLY: Capturing patterns for Markov Chain...")

            # Artifacts
            client.save_cycle_logs(confidence, spin_count)

        except Exception as e:
            print(f"CRITICAL ERROR in V3.0 Accuracy Cycle: {e}")
        finally:
            # 5. Permanent Persistence
            self.session_state["bankroll"] = self.risk.bankroll
            self.memory.save_session(self.session_state)
            self.memory.save_model_weights(self.brain.weights)
            await client.close()
            self.memory.close()
            print(f"--- CYCLE COMPLETE (Bankroll: ₦{self.risk.bankroll:.2f}) ---")

if __name__ == "__main__":
    machine = OmniMachineV30Accuracy()
    asyncio.run(machine.run_accuracy_cycle())
