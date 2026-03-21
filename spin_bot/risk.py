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
            print(f"Peak Equity Updated: ₦{self.bankroll:.2f}")

    def check_circuit_breaker(self) -> bool:
        """Returns True if the system should pause (Drawdown > 15%)."""
        peak = self.state.get("peak_equity", self.bankroll)
        drawdown = (peak - self.bankroll) / peak if peak > 0 else 0

        # Drawdown Control (Reduce Stake by 50% if > 15% drawdown)
        if drawdown > 0.15:
            print(f"Circuit Breaker: Drawdown {drawdown:.2%} detected.")
            return True

        if self.state.get("consecutive_losses", 0) >= 4:
            print("Circuit Breaker: 4 consecutive losses detected.")
            return True

        return False

    def calculate_stake(self, win_prob: float, confidence: float) -> float:
        """Kelly-inspired staking logic (bankroll * edge * confidence_factor)."""
        if self.state["mode"] == "TUITION":
            return 10.0 # Flat tuition stake (₦10)

        # Sniper Mode Staking (₦10 - ₦100)
        # Edge = (P_win * payout) - 1.0 (Assume payout = 1.95x stake)
        edge = (win_prob * 1.95) - 1.0
        if edge <= 0: return 0.0

        # stake = bankroll * edge * confidence_factor
        # Using a conservative multiplier (0.5x edge) for Kelly
        stake = self.bankroll * (edge * 0.5) * confidence

        # Apply Drawdown stake reduction
        peak = self.state.get("peak_equity", self.bankroll)
        drawdown = (peak - self.bankroll) / peak if peak > 0 else 0
        if drawdown > 0.15:
            print("Staking Reduction: Reducing stake by 50% due to drawdown.")
            stake *= 0.5

        # Constraints
        min_stake = 10.0
        max_stake = self.bankroll * 0.05 # 5% bankroll max

        return min(max(stake, min_stake), max_stake, 100.0)

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
            # Target Scaling: Secure 60%, Reinvest 40%
            # If win, increase peak_equity tracking
            self.update_peak_equity()
        else:
            self.state["consecutive_losses"] += 1

        if self.state["mode"] == "TUITION":
            self.state["tuition_spins"] += 1

        self.check_vault()
        print(f"Post-Trade Status: Mode={self.state['mode']} | Balance=₦{self.bankroll:.2f}")
