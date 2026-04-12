import os
import sys
import asyncio
from typing import List, Dict, Optional, Any
from spin_bot.models import EnsembleBrain
from spin_bot.risk import RiskEngine
from spin_bot.executor import DecisionExecutor
from spin_bot.database import TitanDatabase
from spin_bot.auth_engine import TitanAuthEngine
from spin_bot.game_engine import TitanGameEngine
from spin_bot.api_client import OmniAPIClient, normalize_url
from datetime import datetime, timezone

class OmniMachineV31Refined:
    def __init__(self):
        # 1. Initialize Modular Database
        self.db = TitanDatabase()

        # 2. Reconstruct System State
        session = self.db.load_bot_session()
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
        weights = self.db.load_model_weights()
        self.brain = EnsembleBrain(weights)

        # 4. Risk Engine & Staking Logic
        self.risk = RiskEngine(self.session_state["bankroll"], self.session_state)

        # 5. Prediction Engine
        self.executor = DecisionExecutor(self.brain, self.risk)

    async def run_accuracy_cycle(self):
        """V5.52: Modular Unmasked Money Machine."""
        print(f"--- OMNI MACHINE CYCLE V5.52 (UNMASKED-PROT) ---")

        # 1. Component Initialization
        db = TitanDatabase()
        auth = TitanAuthEngine(db)
        engine = TitanGameEngine(db)

        scraped = []

        try:
            # 2. AUTHENTICATION GATE (API/STERILIZED BYPASS)
            print("DEBUG: Securing Session Gate...")
            if not os.getenv("FOOTBALL_NG_LOGIN") or not os.getenv("FOOTBALL_NG_PASS"):
                print("CRITICAL: Missing GitHub Secrets.")
                sys.exit(1)

            if await auth.ensure_session():
                print("DEBUG: Session Secured.")
            else:
                print("CRITICAL: Authentication Gate Failed.")
                sys.exit(1)

            # 3. Betting Environment Entry (Isolated Game Engine)
            print("DEBUG: Launching Isolated Game Engine...")
            state = db.load_storage_state()
            pw, browser, context, page = await engine.run_environment(storage_state=state)

            try:
                print("DEBUG: Anchoring to Spin da Bottle...")
                await page.goto(engine.game_url, wait_until="networkidle")

                game_frame = await engine.get_frame(page)
                print("DEBUG: Environment Ready.")

                # Final Sync and Processing
                api = OmniAPIClient(session_data={"cookies": state.get("cookies", []) if state else []})
                api_history = api.get_spin_history()
                if api_history:
                    scraped = api_history
                else:
                    extraction = await self._capture_history_ui(game_frame)
                    scraped = extraction

                # V5.41: Pass context to log_spin to enable deduplication hashing
                for i, outcome in enumerate(scraped):
                    hist_ctx = scraped[:i]
                    self.db.log_spin(outcome, history_context=hist_ctx)

                # Immortal Session Maintenance
                fresh_state = await context.storage_state()
                self.db.save_storage_state(fresh_state)

                # 4. Accuracy Protocol
                all_spins = self.db.get_latest_spins(500)
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

            finally:
                await context.close()
                await browser.close()
                await pw.stop()

        except Exception as e:
            print(f"CRITICAL ERROR in V5.52 Cycle: {e}")
        finally:
            self.session_state["bankroll"] = self.risk.bankroll
            self.db.save_bot_session(self.session_state)
            self.db.save_model_weights(self.brain.weights)
            self.db.close()
            print(f"--- V5.52 CYCLE COMPLETE (Bankroll: ₦{self.risk.bankroll:.2f}) ---")

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
