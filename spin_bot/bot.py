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

class OmniMachineV31Refined:
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
        """V3.1 Refined: Emergency Repair Integration."""
        print(f"--- OMNI MACHINE CYCLE V3.1 (STEALTH RECOVERY) ---")
        client = PlaywrightClient("https://www.football.com")
        api = OmniAPIClient()

        try:
            # 1. Setup with Persistence (CRITICAL: Load cookies BEFORE navigation)
            existing_cookies = self.memory.load_cookies()
            await client.setup(cookies=existing_cookies)

            # 2. Anti-Redirect Navigation
            if not await client.navigate_to_game():
                print("DEBUG: Direct navigation failed. Attempting login refresh...")
                await client.login()

                # Save fresh session state IMMEDIATELY after login
                new_cookies = await client.get_session_cookies()
                self.memory.save_cookies(new_cookies)
                api.apply_session({"cookies": new_cookies})

                if not await client.navigate_to_game():
                    print("CRITICAL: Failed to reach Game Environment even after login.")
                    await client.page.screenshot(path="artifacts/error.png")
                    return

            # V5.11.0: Betting Environment Entry & Verification
            try:
                print("DEBUG: Entering and Verifying Betting Environment (60s timeout)...")
                # V5.11.0: Explicit wait for 'UP' or 'DOWN' buttons as absolute proof of game load
                # The PlaywrightClient already handles the transition/fallback
                if not client.game_frame:
                    raise Exception("Game Iframe not attached.")

                betting_trigger = client.game_frame.locator("button:has-text('UP'), button:has-text('DOWN'), .m-bet-btn").first
                await betting_trigger.wait_for(state="visible", timeout=60000)
                print("DEBUG: Betting Environment reached and verified.")
            except Exception as e:
                print(f"CRITICAL: Game Environment inaccessible: {e}")
                await client.page.screenshot(path="artifacts/game_fail.png")
                import sys
                sys.exit(1)

            # Save fresh session state
            new_cookies = await client.get_session_cookies()
            self.memory.save_cookies(new_cookies)
            self.memory.save_session_tokens({"cookies": new_cookies}) # V5.11.3: Auth Persistence
            api.apply_session({
                "cookies": new_cookies,
                "endpoints": client.discovered_endpoints
            })

            # Scrape last outcomes with deduplication
            scraped = await client.capture_history_texts()
            for i, outcome in enumerate(scraped):
                context = scraped[:i]
                self.memory.log_spin(outcome, history_context=context)

            # 4. Accuracy Protocol
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

            # PRINT SYSTEM STATE
            print(f"STATE UPDATED: {spin_count} spins recorded. Confidence: {confidence*100:.1f}%")

            # 5. EXECUTION
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
                    print(f"SKIP: No 98% edge. [EV: {decision.get('ev', 0):.2f} | Conf: {confidence:.2f}]")

            client.save_cycle_logs(confidence, spin_count)

        except Exception as e:
            print(f"CRITICAL ERROR in V3.1 Cycle: {e}")
            try: await client.page.screenshot(path="artifacts/error.png")
            except: pass
        finally:
            self.session_state["bankroll"] = self.risk.bankroll
            self.memory.save_session(self.session_state)
            self.memory.save_model_weights(self.brain.weights)
            await client.close()
            self.memory.close()
            print(f"--- CYCLE COMPLETE (Bankroll: ₦{self.risk.bankroll:.2f}) ---")

if __name__ == "__main__":
    machine = OmniMachineV31Refined()
    asyncio.run(machine.run_accuracy_cycle())
