import os
import time
import json
import asyncio
import random
import hashlib
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

        # 6. API Client (Bridge)
        self.api_client = OmniAPIClient()

    async def run_accuracy_cycle(self):
        """V3.0 Refactored Accuracy Protocol Loop."""
        print(f"--- OMNI MACHINE CYCLE V3.0 (MASTER REFACTOR) ---")
        client = PlaywrightClient("https://www.football.com")

        try:
            # 1. Persistence: Load Browser Cookies
            existing_cookies = self.memory.load_cookies()
            await client.setup(cookies=existing_cookies)

            # 2. Authentication: Check Session or Login
            # Try to go to lobby directly
            await client.page.goto("https://www.football.com/ng/games/lobby", wait_until="networkidle")

            # If redirected to login or login button is visible, perform full login
            is_logged_in = not await client.page.locator("text=Login").first.is_visible()
            if not is_logged_in:
                await client.login()
                # Save new cookies
                new_cookies = await client.get_session_cookies()
                self.memory.save_cookies(new_cookies)

            # 3. Bridge: Inject Cookies into API Client
            active_cookies = await client.get_session_cookies()
            # Bridge to Requests Session
            self.api_client.session.cookies.update({c['name']: c['value'] for c in active_cookies})

            # 4. Pattern Discovery: Iframe Context
            if not await client.enter_game_environment():
                print("CRITICAL: Failed to reach Game Environment.")
                return

            # Scrape and Deduplicate
            scraped = await client.capture_history_texts()
            latest_captured = self.memory.get_latest_spins(5)

            for i, outcome in enumerate(scraped):
                # V3.0 Data Integrity: Hash last 5 outcomes
                # To prevent re-logging history from previous runs
                # We log each outcome using its preceding context
                context = scraped[:i]
                self.memory.log_spin(outcome, history_context=context)

            # 5. Accuracy Protocol
            all_spins = self.memory.get_latest_spins(500)
            spin_count = len(all_spins)
            probs = self.brain.predict(all_spins)
            confidence = abs(probs["U"] - 0.5) * 2.0

            if spin_count < 200:
                self.session_state["mode"] = "LEARNING_MODE"
                print(f"98% PROTOCOL: LEARNING_MODE active. ({spin_count}/200 spins)")
            else:
                self.session_state["mode"] = "ELITE_EXECUTION"
                print(f"98% PROTOCOL: ELITE_EXECUTION unlocked. (N={spin_count})")

            print(f"STATE UPDATED: {spin_count} spins recorded. Confidence: {confidence*100:.1f}%")

            # 6. EXECUTION
            if self.session_state["mode"] == "ELITE_EXECUTION":
                decision = self.executor.decide(all_spins)
                if decision["action"] == "BET" and decision["ev"] > 0.05 and confidence > 0.7:
                    print(f"ELITE BET: ₦{decision['amount']} on {decision['direction']}")
                    success = await client.place_ui_bet(decision["direction"], decision["amount"])
                    if success:
                        await asyncio.sleep(15)
                        new_res = await client.capture_history_texts()
                        if new_res:
                            actual = new_res[-1]
                            win = (actual == decision["direction"])
                            if actual == "M": win = False
                            print(f"RESULT: {'WIN' if win else 'LOSS'} (Outcome: {actual})")
                            self.brain.update_weights(all_spins, actual)
                            payout = decision["amount"] * 1.95 if win else 0
                            self.risk.bankroll += (payout - decision["amount"])
                            self.risk.update_result(win)
                else:
                    print(f"SKIP: No valid edge. [EV: {decision.get('ev', 0):.2f} | Conf: {confidence:.2f}]")

            # Artifacts
            client.save_cycle_logs(confidence, spin_count)

        except Exception as e:
            print(f"CRITICAL ERROR in V3.0 accuracy cycle: {e}")
        finally:
            self.session_state["bankroll"] = self.risk.bankroll
            self.memory.save_session(self.session_state)
            self.memory.save_model_weights(self.brain.weights)
            await client.close()
            self.memory.close()
            print(f"--- CYCLE COMPLETE (Bankroll: ₦{self.risk.bankroll:.2f}) ---")

if __name__ == "__main__":
    machine = OmniMachineV30Accuracy()
    asyncio.run(machine.run_accuracy_cycle())
