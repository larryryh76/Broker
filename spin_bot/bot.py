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

class OmniMachineV59:
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

    async def run_ui_cycle(self):
        """V5.9 Primary Execution Loop: Robust Iframe & Selector."""
        print(f"--- STARTING OMNI MACHINE CYCLE V5.9 (ROBUST) ---")
        client = PlaywrightClient(os.getenv("LOGIN_URL", "https://www.football.com/ng/m/search"))

        try:
            # 1. Setup and Navigate (Bypassing Pop-ups)
            await client.setup()
            await client.login()
            await client.navigate_to_game_lobby()

            if not await client.select_spin_game():
                print("CRITICAL: Failed to enter Spin da Bottle game environment.")
                return

            # 2. Execution Loop
            max_rounds = 5
            for round_num in range(max_rounds):
                print(f"DEBUG: Round {round_num + 1}/{max_rounds}")

                # 2a. UI Observation (Iframe context)
                outcomes = await client.get_ui_history_bubbles()
                if not outcomes:
                    print("DEBUG: History not yet visible in frame. Waiting...")
                    await asyncio.sleep(5)
                    continue

                print(f"Observed UI Intelligence: {''.join(outcomes[-10:])}")
                for o in outcomes: self.memory.log_spin(o)

                # 2b. Decision
                full_history = self.memory.get_latest_spins(100)
                decision = self.executor.decide(full_history)

                if decision["action"] == "BET":
                    # 2c. UI Interaction (Text-based locators)
                    success = await client.click_bet_button(decision["direction"], decision["amount"])
                    if success:
                        print(f"Bet placed. Waiting for round resolution...")
                        await asyncio.sleep(15)

                        # Verify result
                        new_outcomes = await client.get_ui_history_bubbles()
                        if new_outcomes:
                            actual = new_outcomes[-1]
                            win = (actual == decision["direction"])
                            if actual == "M": win = False

                            print(f"RESULT: {'WIN' if win else 'LOSS'} (Outcome: {actual})")

                            self.brain.update_weights(full_history, actual)
                            payout = decision["amount"] * 1.95 if win else 0
                            self.risk.bankroll += (payout - decision["amount"])
                            self.risk.update_result(win)
                else:
                    print(f"SKIP: {decision['reason']}")
                    await asyncio.sleep(10)

            # Final Intelligence Dump
            final_history = await client.get_ui_history_bubbles()
            print(f"--- FINAL CYCLE HISTORY: {''.join(final_history[-20:])} ---")
            client.save_network_logs() # Human-readable audit

        except Exception as e:
            print(f"CRITICAL ERROR in V5.9 UI Cycle: {e}")
        finally:
            # 3. Permanent Persistence
            self.session_state["bankroll"] = self.risk.bankroll
            self.memory.save_session(self.session_state)
            self.memory.save_model_weights(self.brain.weights)
            await client.close()
            self.memory.close()
            print(f"--- CYCLE COMPLETE (Bankroll: ₦{self.risk.bankroll:.2f}) ---")

if __name__ == "__main__":
    machine = OmniMachineV59()
    asyncio.run(machine.run_ui_cycle())
