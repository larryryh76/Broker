import os
import time
from typing import List, Dict, Optional
from spin_bot.memory import MemoryGraph
from spin_bot.models import EnsembleBrain
from spin_bot.risk import RiskEngine
from spin_bot.executor import DecisionExecutor
from spin_bot.playwright_client import PlaywrightClient
from datetime import datetime, timezone

class OmniMachineV4:
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

    def run_cycle(self):
        print(f"--- STARTING OMNI MACHINE CYCLE V4 ({self.session_state['mode']}) ---")

        # Failsafe around entire execution
        try:
            # 1. Observation Phase
            client = PlaywrightClient(os.getenv("SPIN_URL", "https://football.com/ng/games/spin"))
            try:
                client.navigate_to_spin_game()

                # 2. Self-Healing Scraping
                # IF selector exists → use it | IF fails → fallback to auto-detection
                history_selector = self.session_state.get("selectors", {}).get("history", "")
                outcomes = []

                # Try existing selector
                if history_selector:
                    try:
                        items = client.page.query_selector_all(history_selector)
                        outcomes = [el.inner_text().strip().upper()[0] for el in items if el.inner_text().strip()]
                    except:
                        pass

                # Fallback to pattern detection
                if not outcomes:
                    outcomes = client.detect_repeating_patterns()
                    if outcomes:
                        # Store pattern for future use if it was robust (pseudo-code for selector generation)
                        self.session_state["selectors"]["history"] = ".history-item" # Hypothetical robust selector

                # 3. Intelligence Phase
                if outcomes:
                    print(f"Observed outcomes: {''.join(outcomes)}")
                    for o in outcomes: self.memory.log_spin(o)

                    full_history = self.memory.get_latest_spins(100)
                    decision = self.executor.decide(full_history)

                    if decision["action"] == "BET":
                        # Detect betting elements for execution
                        ui = client.detect_betting_elements()
                        if ui["up"] and ui["down"] and ui["amount"]:
                            print(f"Executing Bet: ₦{decision['amount']} on {decision['direction']}")

                            # Interaction with jitter
                            ui["amount"].click()
                            ui["amount"].fill(str(decision["amount"]))
                            target = ui["up"] if decision["direction"] == "U" else ui["down"]
                            target.hover()
                            target.click()

                            # Wait for result and update models
                            time.sleep(15)
                            new_outcomes = client.detect_repeating_patterns()
                            if new_outcomes:
                                actual = new_outcomes[-1]
                                win = (actual == decision["direction"])
                                print(f"RESULT: {'WIN' if win else 'LOSS'} (Outcome: {actual})")

                                # Adaptation
                                self.brain.update_weights(full_history, actual)
                                payout = decision["amount"] * 1.95 if win else 0
                                self.risk.bankroll += (payout - decision["amount"])
                                self.risk.update_result(win)
                        else:
                            print("CRITICAL: Betting elements not found. Switching to Observation Mode.")
                            client.take_screenshot("ui_detection_failure")
                    else:
                        print(f"SKIP: {decision['reason']}")
                else:
                    print("CRITICAL: Scraper failed to identify history. Logging error.")
                    client.take_screenshot("scraping_failure")

            except Exception as e:
                print(f"Error during browser interaction: {e}")
                client.take_screenshot("interaction_failure")
            finally:
                client.close()

        except Exception as e:
            print(f"CRITICAL ERROR in Run Cycle: {e}")
        finally:
            # 4. Permanent Persistence Phase (Save State)
            self.session_state["bankroll"] = self.risk.bankroll
            self.memory.save_session(self.session_state)
            self.memory.save_model_weights(self.brain.weights)
            self.memory.close()
            print(f"--- CYCLE COMPLETE (Bankroll: ₦{self.risk.bankroll:.2f}) ---")

if __name__ == "__main__":
    machine = OmniMachineV4()
    machine.run_cycle()
