import config

class RiskManagement:
    def __init__(self, account_info, virtual_equity):
        self.balance = account_info.get("balance", 0)
        self.virtual_equity = virtual_equity

    def calculate_lot_size(self, current_day):
        # Hyper-Compounding Logic
        # Targets: $5 -> $50 (Day 1) -> $250 (Day 2) -> $1500 (Day 3)
        if self.virtual_equity < config.COMPOUNDING_THRESHOLD:
            # Phase 1: Micro-lot enforcement (0.01 lot until $50 as per brief)
            lot = 0.01
        else:
            # Phase 2: Exponential scaling (0.1 lot per $100)
            lot = 0.1 * (self.virtual_equity / 100.0)

        # Supreme Authority: Risk per trade up to 20%
        # This lot size calculation is already very aggressive for a $5 base.
        return max(0.01, round(lot, 2))

    def get_levels(self, side, price, atr):
        # 1:3 RRR for growth
        multiplier = 1.5
        risk = atr * multiplier

        if side == "BUY":
            sl = price - risk
            tp = price + (risk * 3.0)
        else:
            sl = price + risk
            tp = price - (risk * 3.0)

        return round(sl, 5), round(tp, 5)

    def check_circuit_breaker(self, initial_daily_equity):
        # 20% Daily Drawdown Limit for the Autonomous Machine
        drawdown = (initial_daily_equity - self.virtual_equity) / initial_daily_equity
        if drawdown >= config.DAILY_DRAWDOWN_LIMIT:
            return True
        return False
