from trading_bot import config

class RiskManagement:
    def __init__(self, account_info, virtual_equity):
        self.balance = account_info.get("balance", 0)
        self.virtual_equity = virtual_equity

    def calculate_lot_size(self, current_day):
        # Aggressive $5 -> 10X Risk Engine
        # Risk per trade: 10% - 25% of virtual equity
        risk_percent = 0.20

        # dynamic lot = balance * risk_percent / stop_loss_in_points
        # Using a fixed denominator for simplified aggressive scaling if ATR is unknown
        lot = (self.virtual_equity * risk_percent) / 5.0 # Scaled for aggressive growth

        # Ensure minimum lot
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
