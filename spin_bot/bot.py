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

class OmniMachineV58:
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
        """V5.8 Primary Execution Loop: UI-Driven."""
        print(f"--- STARTING OMNI MACHINE CYCLE V5.8 (UI-DRIVEN) ---")
        client = PlaywrightClient(os.getenv("LOGIN_URL", "https://www.football.com/ng/m/search"))

        try:
            # 1. Setup and Navigate
            await client.setup()
            await client.login()
            await client.navigate_to_game_lobby()

            if not await client.select_spin_game():
                print("CRITICAL: Failed to enter Spin da Bottle game.")
                return

            # 2. Configure Game Environment
            await client.enable_one_tap_bet()

            # 3. Execution Loop (Calibration / Sniper)
            max_rounds = 5 # Execution safety for GitHub Actions timeout
            for round_num in range(max_rounds):
                print(f"DEBUG: Round {round_num + 1}/{max_rounds}")

                # 3a. UI Observation
                outcomes = await client.get_ui_history_bubbles()
                if not outcomes:
                    print("DEBUG: History bubbles not yet visible. Waiting...")
                    await asyncio.sleep(5)
                    continue

                print(f"Observed UI Intelligence: {''.join(outcomes[-10:])}")
                for o in outcomes: self.memory.log_spin(o)

                # 3b. Decision
                full_history = self.memory.get_latest_spins(100)
                decision = self.executor.decide(full_history)

                if decision["action"] == "BET":
                    # 3c. UI Interaction
                    success = await client.click_bet_button(decision["direction"])
                    if success:
                        # Wait for round resolution
                        print(f"Bet placed. Waiting for result...")
                        await asyncio.sleep(15)

                        # Verify result
                        new_outcomes = await client.get_ui_history_bubbles()
                        if new_outcomes:
                            actual = new_outcomes[-1]
                            win = (actual == decision["direction"])

                            # Handle 'M' (Middle) Loss correctly
                            if actual == "M":
                                win = False
                                print("HOUSE EDGE: Bottle stopped in MIDDLE. Automatic LOSS.")

                            print(f"RESULT: {'WIN' if win else 'LOSS'} (Outcome: {actual})")

                            # Update system
                            self.brain.update_weights(full_history, actual)
                            payout = decision["amount"] * 1.95 if win else 0
                            self.risk.bankroll += (payout - decision["amount"])
                            self.risk.update_result(win)
                else:
                    print(f"SKIP: {decision['reason']}")
                    await asyncio.sleep(10) # Observation interval

            client.save_network_logs() # Background discovery capture

        except Exception as e:
            print(f"CRITICAL ERROR in V5.8 UI Cycle: {e}")
        finally:
            # 4. Permanent Persistence
            self.session_state["bankroll"] = self.risk.bankroll
            self.memory.save_session(self.session_state)
            self.memory.save_model_weights(self.brain.weights)
            await client.close()
            self.memory.close()
            print(f"--- CYCLE COMPLETE (Bankroll: ₦{self.risk.bankroll:.2f}) ---")

if __name__ == "__main__":
    machine = OmniMachineV58()
    asyncio.run(machine.run_ui_cycle())
