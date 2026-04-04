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
        self.session_state = self.memory.load_session() or {
            "bankroll": 1000.0,
            "mode": "TUITION",
            "peak_equity": 1000.0,
            "vault_locked": False,
            "history": [],
            "tuition_history": [],
            "tuition_spins": 0
        }

        # 3. Model Weight Loading
        weights = self.memory.load_model_weights()
        self.brain = EnsembleBrain(weights)

        # 4. Risk Engine & Staking Logic
        self.risk = RiskEngine(self.session_state["bankroll"], self.session_state)

        # 5. Prediction Engine
        self.executor = DecisionExecutor(self.brain, self.risk)

    async def run_accuracy_cycle(self):
        """V5.28.1: OMNI-RECURSIVE TITAN MACHINE (HEURISTIC INTERCEPTOR)."""
        print(f"--- OMNI MACHINE CYCLE V5.28.1 (INTERCEPTOR PROTOCOL) ---")

        # 1. Titan-Stealth Initialization
        client = TitanStealthClient()

        api_success = False
        scraped = []

        try:
            # 2. TITAN AUTH (DYNAMIC SNIFFING)
            print("DEBUG: Executing Titan-Stealth Auth Sequence...")
            # Ensure critical vars are present
            if not os.getenv("FOOTBALL_NG_LOGIN") or not os.getenv("FOOTBALL_NG_PASS"):
                print("CRITICAL: Missing GitHub Secrets (FOOTBALL_NG_LOGIN/PASS).")
                sys.exit(1)

            # Perform Login
            if await client.login():
                print("DEBUG: Titan Landing Success.")
            else:
                print("CRITICAL: Titan Protocol failed. Terminating to prevent flagging.")
                sys.exit(1)

            # 3. Betting Environment Entry & Verification
            print("DEBUG: Entering and Verifying Betting Environment...")
            target_url = "https://www.football.com/ng/games/spin-da-bottle"
            await client.page.goto(target_url, wait_until="networkidle")

            # Standard transition
            await client.hide_init_loader()

            # Modal handling on game page
            try:
                close_btn = client.page.locator('i.m-icon-close[data-op="region-close"]')
                if await close_btn.is_visible(): await close_btn.click()
            except: pass

            # Iframe Sync
            game_frame = client.page.frame_locator("iframe[src*='sportygames']")
            ui_indicator = game_frame.locator("canvas, .history, .results, .history-list, .bet-panel").first
            await ui_indicator.wait_for(state="visible", timeout=45000)
            print("DEBUG: Betting Environment reached and verified.")

            # 4. Final Sync and Processing
            new_storage = await client.context.storage_state()
            # Bridge to OmniAPIClient for history retrieval
            api = OmniAPIClient(session_data={"storage_state": new_storage, "discovered_login_url": client.discovered_login_url})

            api_history = api.get_spin_history()
            if api_history:
                scraped = api_history
            else:
                # Fallback to UI scrape
                extraction = await self._capture_history_ui(game_frame)
                scraped = extraction

            # Deduplication and mental state update
            for i, outcome in enumerate(scraped):
                context = scraped[:i]
                self.memory.log_spin(outcome, history_context=context)

            # Accuracy Protocol
            all_spins = self.memory.get_latest_spins(500)
            spin_count = len(all_spins)
            probs = self.brain.predict(all_spins)
            confidence = abs(probs["U"] - 0.5) * 2.0

            if spin_count < 200:
                self.session_state["mode"] = "TUITION"
                print(f"98% PROTOCOL: TUITION active. ({spin_count}/200 spins)")
            else:
                self.session_state["mode"] = "SNIPER"
                print(f"98% PROTOCOL: SNIPER Active. (N={spin_count})")

            # 5. EXECUTION
            if self.session_state["mode"] == "SNIPER":
                decision = self.executor.decide(all_spins)
                if decision["action"] == "BET" and decision["ev"] > 0.05 and confidence > 0.7:
                    print(f"ELITE BET: ₦{decision['amount']} on {decision['direction']}")

                    bet_success = await self._place_frame_bet(game_frame, decision["direction"], decision["amount"])

                    if bet_success:
                        await asyncio.sleep(15)
                        # Result verification
                        outcomes = api.get_spin_history()
                        if outcomes:
                            actual = outcomes[-1]
                            win = (actual == decision["direction"])
                            if actual == "M": win = False
                            print(f"RESULT: {'WIN' if win else 'LOSS'} (Outcome: {actual})")
                            self.brain.update_weights(all_spins, actual)
                            self.risk.bankroll += (decision["amount"] * 1.95 if win else -decision["amount"])
                            self.risk.update_result(win)
                else:
                    print(f"SKIP: No 98% edge. [EV: {decision.get('ev', 0):.2f}]")

        except Exception as e:
            print(f"CRITICAL ERROR in V5.28.1 Cycle: {e}")
            await client.capture_failure("cycle_crash")
        finally:
            self.session_state["bankroll"] = self.risk.bankroll
            self.memory.save_session(self.session_state)
            self.memory.save_model_weights(self.brain.weights)
            await client.close()
            self.memory.close()
            print(f"--- V5.28.1 CYCLE COMPLETE (Bankroll: ₦{self.risk.bankroll:.2f}) ---")

    async def _capture_history_ui(self, frame) -> List[str]:
        results = []
        try:
            # Bug Fix: don't use .first if we want all texts
            loc = frame.locator(".history-item, .result-item, .history_ball")
            texts = await loc.all_inner_texts()
            for text in texts:
                t = text.strip().upper()
                if "UP" in t or "U" in t: results.append("U")
                elif "DOWN" in t or "D" in t: results.append("D")
                elif "MIDDLE" in t or "M" in t: results.append("M")
            return results[::-1] # Ensure chronological
        except: return []

    async def _place_frame_bet(self, frame, direction: str, amount: float) -> bool:
        try:
            await frame.locator('input[type="number"]').first.fill(str(amount))
            target = "UP" if direction == "U" else "DOWN"
            await frame.locator("button", has_text=target).first.click(force=True)
            return True
        except: return False

if __name__ == "__main__":
    machine = OmniMachineV31Refined()
    asyncio.run(machine.run_accuracy_cycle())
