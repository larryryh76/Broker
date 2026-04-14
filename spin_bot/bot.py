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
from spin_bot.api_client import OmniAPIClient
from datetime import datetime, timezone

class OmniMachineV31Refined:
    def __init__(self):
        self.db = TitanDatabase()
        session = self.db.load_bot_session()
        if not session or session.get("bankroll", 0) <= 0:
            session = {"bankroll": 300.0, "mode": "TUITION", "peak_equity": 300.0, "vault_locked": False}
        self.session_state = session
        weights = self.db.load_model_weights()
        self.brain = EnsembleBrain(weights)
        self.risk = RiskEngine(self.session_state["bankroll"], self.session_state)
        self.executor = DecisionExecutor(self.brain, self.risk)

    async def run_accuracy_cycle(self):
        """V5.58: Modular Gatekeeper Money Machine."""
        print("--- OMNI MACHINE CYCLE V5.58 (GATEKEEPER) ---")
        db = TitanDatabase()
        auth = TitanAuthEngine(db)
        engine = TitanGameEngine(db)

        try:
            if not await auth.ensure_session():
                print("CRITICAL: Auth failed.")
                sys.exit(1)

            state = db.load_storage_state()
            pw, browser, context, page = await engine.run_environment(storage_state=state)

            try:
                game_frame = await engine.get_frame(page)

                # Capture and Log
                api = OmniAPIClient(session_data={"cookies": state.get("cookies", []) if state else []})
                scraped = api.get_spin_history()
                if not scraped:
                    scraped = await self._capture_history_ui(game_frame)

                for i, outcome in enumerate(scraped):
                    self.db.log_spin(outcome, history_context=scraped[:i])

                fresh_state = await context.storage_state()
                self.db.save_storage_state(fresh_state)

                # Logic & Betting
                all_spins = self.db.get_latest_spins(500)
                if len(all_spins) < 200:
                    print(f"98% PROTOCOL: TUITION ({len(all_spins)}/200)")
                else:
                    decision = self.executor.decide(all_spins)
                    if decision["action"] == "BET":
                        print(f"ELITE BET: {decision['amount']} on {decision['direction']}")
                        if await self._place_frame_bet(game_frame, decision["direction"], decision["amount"]):
                            print("RESULT: SUCCESSFUL PLACEMENT.")
            finally:
                await context.close()
                await browser.close()
                await pw.stop()

        except Exception as e:
            print(f"CRITICAL ERROR: {e}")
        finally:
            self.session_state["bankroll"] = self.risk.bankroll
            self.db.save_bot_session(self.session_state)
            self.db.save_model_weights(self.brain.weights)
            self.db.close()
            print(f"--- CYCLE COMPLETE (Bankroll: ₦{self.risk.bankroll:.2f}) ---")

    async def _capture_history_ui(self, frame) -> List[str]:
        results = []
        try:
            loc = frame.locator(".history-item, .result-item, .history_ball")
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
