from typing import Dict, Optional

from datetime import datetime, timezone, timedelta

class RiskEngine:
    def __init__(self, bankroll: float, session_state: Dict):
        self.bankroll = bankroll
        self.state = session_state or {
            "mode": "TUITION",
            "consecutive_losses": 0,
            "peak_equity": bankroll,
            "vault_locked": False,
            "tuition_spins": 0,
            "shutdown_until": None,
            "target_multiplier": 10,
            "min_balance": 500.0 # V5.17.0 Floor protection
        }

    def update_peak_equity(self):
        if self.bankroll > self.state.get("peak_equity", 0):
            self.state["peak_equity"] = self.bankroll
            print(f"Peak Equity Updated: ₦{self.bankroll:.2f}")

    def check_circuit_breaker(self) -> bool:
        """V5.17.0: Enhanced Circuit Breaker (Floor + 3-Strike Rule)."""
        # 0. Shutdown Check
        shutdown_ts = self.state.get("shutdown_until")
        if shutdown_ts:
            if isinstance(shutdown_ts, str):
                shutdown_ts = datetime.fromisoformat(shutdown_ts)
            if datetime.now(timezone.utc) < shutdown_ts:
                print(f"CIRCUIT BREAKER: System in cooling mode until {shutdown_ts}")
                return True

        # 1. Floor Protection (The Vault)
        min_bal = self.state.get("min_balance", 500.0)
        if self.bankroll < min_bal:
            print(f"VAULT PROTECTION: Balance ₦{self.bankroll} < {min_bal}. Betting halted.")
            return True

        # 2. Drawdown Control
        peak = self.state.get("peak_equity", self.bankroll)
        drawdown = (peak - self.bankroll) / peak if peak > 0 else 0
        if drawdown > 0.15:
            print(f"Circuit Breaker: Drawdown {drawdown:.2%} detected.")
            return True

        # 3. V5.15.0 3-Strike Rule
        if self.state.get("consecutive_losses", 0) >= 3:
            print("3-STRIKE RULE: 3 consecutive losses. Shutting down for 6 hours.")
            self.state["shutdown_until"] = (datetime.now(timezone.utc) + timedelta(hours=6)).isoformat()
            return True

        return False

    def calculate_stake(self, win_prob: float, confidence: float) -> float:
        """Kelly-inspired staking logic (bankroll * edge * confidence_factor)."""
        if self.check_circuit_breaker():
            return 0.0 # STOP

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
            self.update_peak_equity()

            # V5.17.0 Tuition history update
            if self.state["mode"] == "TUITION":
                if "tuition_history" not in self.state: self.state["tuition_history"] = []
                self.state["tuition_history"].append(1)

            # V5.17.0 Target Scaling & Profit Securing (10X Recursive)
            base_capital = 500.0
            realized_profit = self.bankroll - base_capital
            if realized_profit > 0:
                current_target = base_capital + (realized_profit * 10) # 10x Escalation logic

                # Check for securing profit (50% rule)
                if realized_profit >= 1000: # Arbitrary threshold for securing
                    secure_amount = realized_profit * 0.5
                    new_floor = base_capital + secure_amount
                    if new_floor > self.state.get("min_balance", 500):
                        print(f"V5.17 PROFIT SECURED: Setting new floor to ₦{new_floor:.2f}")
                        self.state["min_balance"] = new_floor

                if self.bankroll >= 10000: # Scaling target
                    print(f"V5.17 TARGET HIT. Moving to next recursion level.")
        else:
            self.state["consecutive_losses"] += 1
            if self.state["mode"] == "TUITION":
                if "tuition_history" not in self.state: self.state["tuition_history"] = []
                self.state["tuition_history"].append(0)

        if self.state["mode"] == "TUITION":
            self.state["tuition_spins"] += 1
            # Note: Win Rate check is typically done in bot.py logic

        self.check_vault()
        print(f"Post-Trade Status: Mode={self.state['mode']} | Balance=₦{self.bankroll:.2f}")
