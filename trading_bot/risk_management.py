from trading_bot import config

class RiskManagement:
    def __init__(self, account_info, virtual_equity):
        self.balance = account_info.get("balance", 0)
        self.virtual_equity = virtual_equity
        self.base_capital = 5.0

    def calculate_lot_size(self, current_day=1):
        # 🔥 Money Machine Strategy: $5 Account Core
        # Lot size is FIXED at 0.01 ONLY for the compounding phase
        return 0.01

    def get_levels(self, side, price, atr):
        # Money Machine: Targeting 20-point moves
        # 1:3 RRR for growth
        # Points are usually 0.01 for XAUUSD (1 point = 0.01 price move)
        # 20 points = 0.20 price move
        risk = 0.07 # ~7 points risk
        reward = 0.21 # ~21 points reward (target move)

        if side == "BUY":
            sl = price - risk
            tp = price + reward
        else:
            sl = price + risk
            tp = price - reward

        return round(sl, 2), round(tp, 2)

    def check_circuit_breaker(self, initial_daily_equity):
        # 20% Daily Drawdown Limit
        drawdown = (initial_daily_equity - self.virtual_equity) / initial_daily_equity
        if drawdown >= config.DAILY_DRAWDOWN_LIMIT:
            return True
        return False

    def check_micro_shield(self):
        # Micro-Account Shield: 15% drawdown on $5 base = $0.75
        if self.virtual_equity < (self.base_capital * 0.85):
            return True
        return False
