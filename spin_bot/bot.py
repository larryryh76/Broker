import os
import sys
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
        """V5.13.0 Hybrid: API Client (Primary) + Playwright (Fallback)."""
        print(f"--- OMNI MACHINE CYCLE V5.13.0 (HYBRID) ---")

        # 1. Initialize API Client and check for existing session
        full_session = self.memory.load_full_session()
        api = OmniAPIClient(session_data=full_session)
        client = PlaywrightClient("https://www.football.com")

        api_success = False
        scraped = []

        try:
            # 2. Attempt API Execution (PRIMARY)
            print("DEBUG: Attempting PRIMARY path (API)...")
            user = os.getenv("FOOTBALL_NG_LOGIN")
            pw = os.getenv("FOOTBALL_NG_PASS")

            if api.login(user, pw):
                # V5.13.1: Persistence Sync
                api_cookies = api.session.cookies.get_dict()
                cookie_list = [{"name": k, "value": v, "domain": ".football.com", "path": "/"} for k, v in api_cookies.items()]
                self.memory.save_full_session({"cookies": cookie_list})
                self.memory.save_session_tokens({"cookies": cookie_list})

                api_history = api.get_spin_history()
                if api_history:
                    print(f"DEBUG: API Success. Retrieved {len(api_history)} spins.")
                    scraped = api_history
                    api_success = True

            if not api_success:
                print("DEBUG: API Failed. Falling back to Playwright UI...")
                # 3. Playwright Fallback (UI)
                # Inject cookies from API to bypass login modal if possible
                api_cookies = api.session.cookies.get_dict()
                cookie_list = [{"name": k, "value": v, "domain": ".football.com", "path": "/"} for k, v in api_cookies.items()]

                await client.setup(cookies=cookie_list)

                if not await client.navigate_to_game():
                    print("DEBUG: Nav failure or Session expired. Attempting UI Login...")
                    await client.login()

                    # Capture and sync session immediately
                    new_cookies = await client.get_session_cookies()
                    self.memory.save_full_session({"cookies": new_cookies})
                    api.apply_session({"cookies": new_cookies})

                    if not await client.navigate_to_game():
                        print("CRITICAL: Failed to reach Game Environment even after login.")
                        await client.page.screenshot(path="artifacts/error.png")
                        return

            # V5.13.1: Strict Dashboard Verification (Deposit Button)
            if not api_success:
                try:
                    # Deposit button check as proof of successful landing
                    # Using robust filter to avoid invalid CSS patterns
                    deposit_indicator = client.page.locator("button").filter(has_text="Deposit").first
                    await deposit_indicator.wait_for(state="visible", timeout=30000)
                    print("DEBUG: Dashboard landing verified (Deposit button found).")
                except:
                    print("WARNING: Dashboard verification failed.")
                    await client.page.screenshot(path="artifacts/error.png")

            # V5.11.0: Betting Environment Entry & Verification
            if not api_success:
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
                    try: await client.page.screenshot(path="artifacts/game_fail.png")
                    except: pass
                    sys.exit(1)

            # 4. Final Sync and Processing
            if not api_success:
                new_cookies = await client.get_session_cookies()
                self.memory.save_full_session({"cookies": new_cookies})
                api.apply_session({
                    "cookies": new_cookies,
                    "endpoints": client.discovered_endpoints
                })

                # Structured Data Synchronization
                extraction = await client.capture_history_texts()
                scraped = extraction["results"]

            # Sequence-Hash Deduplication (V5.13.0)
            for i, outcome in enumerate(scraped):
                # Pattern generated from the last 4 outcomes + current
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

                    bet_success = False
                    if api_success:
                        res = api.place_bet(decision["direction"], decision["amount"])
                        if "error" not in res:
                            print(f"API BET SUCCESS: {res}")
                            bet_success = True
                    else:
                        bet_success = await client.place_ui_bet(decision["direction"], decision["amount"])

                    if bet_success:
                        await asyncio.sleep(15)
                        # Re-verify results
                        if api_success:
                            outcomes = api.get_spin_history()
                        else:
                            extraction = await client.capture_history_texts()
                            outcomes = extraction.get("results", [])

                        if outcomes:
                            actual = outcomes[-1]
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
