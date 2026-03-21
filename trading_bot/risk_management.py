from trading_bot import config

class RiskManagement:
    def __init__(self, account_info, virtual_equity):
        self.balance = account_info.get("balance", 0)
        self.virtual_equity = virtual_equity
        self.base_capital = 5.0

    def calculate_lot_size(self, current_day=1):
        # 🔥 Aggressive Micro-Account Logic ($5 Core)
        # Sizing starts at 0.01 lot minimum
        # Scaling kicks in only after substantial growth
        if self.virtual_equity < 50.0:
            return 0.01

        # Sizing for larger accounts
        risk_percent = 0.20
        lot = (self.virtual_equity * risk_percent) / 10.0
        return max(0.01, round(lot, 2))

    def get_levels(self, side, price, atr):
        # 1:3 RRR for growth
        multiplier = 1.5
        risk = max(atr * multiplier, 0.00010) # Minimum 10 points

        if side == "BUY":
            sl = price - risk
            tp = price + (risk * 3.0)
        else:
            sl = price + risk
            tp = price - (risk * 3.0)

        return round(sl, 5), round(tp, 5)

    def check_circuit_breaker(self, initial_daily_equity):
        # 20% Daily Drawdown Limit
        drawdown = (initial_daily_equity - self.virtual_equity) / initial_daily_equity
        if drawdown >= config.DAILY_DRAWDOWN_LIMIT:
            return True
        return False

    def check_micro_shield(self):
        # 🔥 Micro-Account Shield: 15% drawdown on $5 base = $0.75
        # If loss exceeds $0.75 from initial base + bot profit, trigger shield
        current_profit = self.virtual_equity - self.base_capital

        # Note: We track profit/loss from the $5 foundation.
        # If floating drawdown on the account reaches -15% of current virtual equity, stop.
        # Simplified: If current floating loss > 15% of $5 capital (scaled), stop.

        # For the $5 core specifically, we enforce a strict $0.75 protection.
        if self.virtual_equity < (self.base_capital * 0.85):
            return True
        return False
