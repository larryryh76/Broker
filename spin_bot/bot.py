import os
import sys
import asyncio
from typing import List, Dict, Optional, Any
from spin_bot.memory import MemoryGraph
from spin_bot.models import EnsembleBrain
from spin_bot.risk import RiskEngine
from spin_bot.executor import DecisionExecutor
from spin_bot.titan_stealth import TitanStealthClient
from spin_bot.api_client import OmniAPIClient, normalize_url
from datetime import datetime, timezone

class OmniMachineV31Refined:
    def __init__(self):
        # 1. Initialize MongoDB Persistence
        self.memory = MemoryGraph(os.getenv("MONGODB_URI", "mongodb://localhost:27017"))

        # 2. Reconstruct System State
        session = self.memory.load_session()
        if not session or session.get("bankroll", 0) <= 0:
            session = {
                "bankroll": 300.0,
                "mode": "TUITION",
                "peak_equity": 300.0,
                "vault_locked": False,
                "history": [],
                "tuition_history": [],
                "tuition_spins": 0
            }
        self.session_state = session

        # 3. Model Weight Loading
        weights = self.memory.load_model_weights()
        self.brain = EnsembleBrain(weights)

        # 4. Risk Engine & Staking Logic
        self.risk = RiskEngine(self.session_state["bankroll"], self.session_state)

        # 5. Prediction Engine
        self.executor = DecisionExecutor(self.brain, self.risk)

    async def run_accuracy_cycle(self):
        """V5.33: OMNI-RECURSIVE TITAN MACHINE (REPAIR & ANCHOR)."""
        print(f"--- OMNI MACHINE CYCLE V5.33 (REPAIR & ANCHOR) ---")

        # 1. Titan-Stealth Initialization
        client = TitanStealthClient()

        scraped = []

        try:
            # 2. TITAN AUTH (GOLDEN PATH)
            print("DEBUG: Executing Golden Path Auth Sequence...")
            if not os.getenv("FOOTBALL_NG_LOGIN") or not os.getenv("FOOTBALL_NG_PASS"):
                print("CRITICAL: Missing GitHub Secrets.")
                sys.exit(1)

            if await client.login():
                print("DEBUG: Titan Auth Success.")
            else:
                print("CRITICAL: Titan Auth failed.")
                sys.exit(1)

            # 3. Betting Environment Entry (V5.32 Resilient Stealth)
            print("DEBUG: Entering Betting Environment (Direct Navigation)...")
            # Use direct URL to avoid Google redirect detection
            target_url = "https://www.football.com/ng/m/games/spin-da-bottle"
            await client.hard_anchor_navigation(target_url)

            # V5.32 Overlay Killer & Human Jiggle
            await client.stabilize_environment()
            await client.human_jiggle()

            # V5.21.1 Standard Transition
            await client.hide_init_loader()

            # V5.30 Iframe Sync (Direct - No factsCenter wait)
            game_frame = client.page.frame_locator("iframe[src*='sportygames']")
            ui_indicator = game_frame.locator("canvas, .history, .results, .history-list, .bet-panel").first

            try:
                await ui_indicator.wait_for(state="visible", timeout=60000)
                print("DEBUG: Betting Environment fully hydrated.")
            except:
                # Anti-CAPTCHA Check
                content = await client.page.content()
                if "CAPTCHA" in content.upper() or "UNUSUAL TRAFFIC" in content.upper():
                    print("CRITICAL: CAPTCHA detected. IP Flagged. Aborting for 10 min cooldown.")
                    sys.exit(0) # Exit cleanly to let runner sleep

                print("DEBUG: Iframe timeout. Final Stabilize attempt...")
                await client.stabilize_environment()
                await ui_indicator.wait_for(state="visible", timeout=15000)

            # V5.15: Immortalize session upon successful entry
            storage = await client.context.storage_state()
            client.save_storage_state(storage)

            # 4. Final Sync and Processing
            # Extract cookies for API Client compatibility
            api = OmniAPIClient(session_data={"cookies": storage.get("cookies", [])})

            api_history = api.get_spin_history()
            if api_history:
                scraped = api_history
            else:
                extraction = await self._capture_history_ui(game_frame)
                scraped = extraction

            for outcome in scraped:
                self.memory.log_spin(outcome)

            # 4. Accuracy Protocol
            all_spins = self.memory.get_latest_spins(500)
            spin_count = len(all_spins)
            probs = self.brain.predict(all_spins)
            confidence = abs(probs["U"] - 0.5) * 2.0

            if spin_count < 200:
                self.session_state["mode"] = "TUITION"
                print(f"98% PROTOCOL: TUITION active. ({spin_count}/200 spins)")
            else:
                # V5.17 Markov Confidence Escalation check
                from spin_bot.models import MarkovModel
                mm = MarkovModel(all_spins).predict()
                mm_conf = max(mm.values())

                if mm_conf >= 0.60:
                    self.session_state["mode"] = "SNIPER"
                    print(f"98% PROTOCOL: SNIPER Active. (N={spin_count}, Conf: {mm_conf:.2f})")
                else:
                    self.session_state["mode"] = "TUITION"
                    print(f"98% PROTOCOL: TUITION (LEARNING) active due to low confidence ({mm_conf:.2f}).")

            # 5. EXECUTION
            if self.session_state["mode"] == "SNIPER":
                decision = self.executor.decide(all_spins)
                if decision["action"] == "BET" and decision["ev"] > 0.05 and confidence > 0.7:
                    print(f"ELITE BET: ₦{decision['amount']} on {decision['direction']}")

                    bet_success = await self._place_frame_bet(game_frame, decision["direction"], decision["amount"])

                    if bet_success:
                        await asyncio.sleep(15)
                        outcomes = api.get_spin_history()
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

        except Exception as e:
            print(f"CRITICAL ERROR in V5.33 Cycle: {e}")
            await client.capture_failure("cycle_crash")
        finally:
            self.session_state["bankroll"] = self.risk.bankroll
            self.memory.save_session(self.session_state)
            self.memory.save_model_weights(self.brain.weights)
            await client.close()
            self.memory.close()
            print(f"--- V5.33 CYCLE COMPLETE (Bankroll: ₦{self.risk.bankroll:.2f}) ---")

    async def _capture_history_ui(self, frame) -> List[str]:
        results = []
        try:
            loc = frame.locator(".history-item:visible, .result-item:visible, .history_ball:visible")
            texts = await loc.all_inner_texts()
            for text in texts:
                t = text.strip().upper()
                if "UP" in t or "U" in t: results.append("U")
                elif "DOWN" in t or "D" in t: results.append("D")
                elif "MIDDLE" in t or "M" in t: results.append("M")
            return results[::-1]
        except: return []

    async def _place_frame_bet(self, frame, direction: str, amount: float) -> bool:
        try:
            await frame.locator('input[type="number"]:visible').first.fill(str(amount))
            target = "UP" if direction == "U" else "DOWN"
            await frame.locator(f"button:visible:has-text('{target}')").first.click(force=True)
            return True
        except: return False

if __name__ == "__main__":
    machine = OmniMachineV31Refined()
    asyncio.run(machine.run_accuracy_cycle())
