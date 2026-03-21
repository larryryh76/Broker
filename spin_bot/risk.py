from typing import Dict, Optional

class RiskEngine:
    def __init__(self, bankroll: float, session_state: Dict):
        self.bankroll = bankroll
        self.state = session_state or {
            "mode": "TUITION",
            "consecutive_losses": 0,
            "peak_equity": bankroll,
            "vault_locked": False,
            "tuition_spins": 0
        }

    def update_peak_equity(self):
        if self.bankroll > self.state.get("peak_equity", 0):
            self.state["peak_equity"] = self.bankroll

    def check_circuit_breaker(self) -> bool:
        """Returns True if the system should pause (Drawdown > 15%)."""
        peak = self.state.get("peak_equity", self.bankroll)
        drawdown = (peak - self.bankroll) / peak if peak > 0 else 0
        if drawdown > 0.15:
            return True
        if self.state.get("consecutive_losses", 0) >= 3:
            return True
        return False

    def calculate_stake(self, win_prob: float, confidence: float) -> float:
        """Calculates stake based on Kelly-inspired math and mode."""
        if self.state["mode"] == "TUITION":
            return 10.0 # Flat tuition stake (₦10)

        # Sniper Mode Staking (₦10 - ₦50)
        # stake = bankroll * edge * confidence_factor
        edge = (win_prob * 1.95) - 1.0 # 1.95x payout assumed
        if edge <= 0: return 0.0

        stake = self.bankroll * edge * confidence

        # Constraints
        max_stake = self.bankroll * 0.05
        return min(max(stake, 10.0), max_stake, 50.0)

    def check_vault(self):
        """₦500 Vault protection."""
        if self.bankroll >= 800 and not self.state.get("vault_locked", False):
            self.state["vault_locked"] = True
            print("VAULT PROTECTED: ₦500 Locked.")

    def promote_mode(self, win_rate: float):
        """Promotion from Tuition to Sniper mode."""
        if self.state["mode"] == "TUITION":
            if self.state["tuition_spins"] >= 50 and win_rate >= 0.55:
                self.state["mode"] = "SNIPER"
                print("MODE PROMOTED: SNIPER Activated.")

    def update_result(self, win: bool):
        if win:
            self.state["consecutive_losses"] = 0
        else:
            self.state["consecutive_losses"] += 1

        if self.state["mode"] == "TUITION":
            self.state["tuition_spins"] += 1

        self.update_peak_equity()
        self.check_vault()
