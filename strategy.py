import pandas as pd
import pandas_ta as ta
from config import logger, RISK_REWARD_RATIO

class Strategy:
    def __init__(self):
        self.win_rate_threshold = 0.50
        self.performance_multiplier = 1.0

    def adjust_parameters(self, learning_state):
        """
        Recursive Learning: Adjust parameters based on historical performance.
        If win rate is high, we can slightly increase risk.
        If win rate is low, we decrease risk.
        """
        if not learning_state:
            return

        win_rate = learning_state.get("win_rate", 0) / 100
        total_trades = learning_state.get("total_trades", 0)

        # Only adjust after enough data (e.g., 10 trades)
        if total_trades >= 10:
            if win_rate > 0.60:
                self.performance_multiplier = 1.2
            elif win_rate < 0.40:
                self.performance_multiplier = 0.8
            else:
                self.performance_multiplier = 1.0

        logger.info(f"Strategy parameters adjusted: Multiplier={self.performance_multiplier}")

    def prepare_data(self, candles):
        if not candles:
            return None

        data = []
        for candle in candles:
            data.append({
                "time": candle["time"],
                "open": float(candle["mid"]["o"]),
                "high": float(candle["mid"]["h"]),
                "low": float(candle["mid"]["l"]),
                "close": float(candle["mid"]["c"]),
                "volume": int(candle["volume"])
            })

        df = pd.DataFrame(data)
        return df

    def calculate_indicators(self, df):
        if df is None or len(df) < 50:
            return None

        # RSI 14
        df["rsi"] = ta.rsi(df["close"], length=14)

        # Moving Averages: 20-period fast and 50-period slow
        df["ma_fast"] = ta.sma(df["close"], length=20)
        df["ma_slow"] = ta.sma(df["close"], length=50)

        return df

    def generate_signal(self, df):
        if df is None or len(df) < 1:
            return None

        latest = df.iloc[-1]

        # 1. RSI: > 70 SHORT, < 30 LONG
        long_rsi = latest["rsi"] < 30
        short_rsi = latest["rsi"] > 70

        # 2. Price vs MA: Price > MA20 LONG, Price < MA20 SHORT
        long_price_ma = latest["close"] > latest["ma_fast"]
        short_price_ma = latest["close"] < latest["ma_fast"]

        # 3. MA Crossover: MA20 > MA50 LONG, MA20 < MA50 SHORT
        long_ma_cross = latest["ma_fast"] > latest["ma_slow"]
        short_ma_cross = latest["ma_fast"] < latest["ma_slow"]

        # Alignment count
        long_count = sum([long_rsi, long_price_ma, long_ma_cross])
        short_count = sum([short_rsi, short_price_ma, short_ma_cross])

        # Minimum 2 of 3 alignment
        if long_count >= 2:
            confidence = 0.70 if long_count == 2 else 0.85
            # Potential for 95% if strong divergence or other price action (simplified for now)
            return {"side": "BUY", "confidence": confidence, "price": latest["close"]}
        elif short_count >= 2:
            confidence = 0.70 if short_count == 2 else 0.85
            return {"side": "SELL", "confidence": confidence, "price": latest["close"]}

        return {"side": "SKIP", "confidence": 0, "price": latest["close"]}

    def calculate_levels(self, side, price):
        """
        Stop Loss: 2% from entry
        Take Profit: 1:3 ratio
        """
        risk_pct = 0.02
        if side == "BUY":
            stop_loss = price * (1 - risk_pct)
            take_profit = price + (price - stop_loss) * RISK_REWARD_RATIO
        elif side == "SELL":
            stop_loss = price * (1 + risk_pct)
            take_profit = price - (stop_loss - price) * RISK_REWARD_RATIO
        else:
            return None, None

        return stop_loss, take_profit

    def calculate_position_size(self, balance, entry_price, stop_loss, confidence):
        """
        Dynamic Position Sizing:
        - < $100: Risk 2%
        - $100 - $1000: Risk 3%
        - $1000 - $10000: Risk 5%
        - > $10000: Risk 8%

        Confidence Adjustment: (confidence / 0.95)
        Position Cap: 1% of total balance (total value of trade)
        """
        if balance < 100:
            risk_pct = 0.02
        elif balance < 1000:
            risk_pct = 0.03
        elif balance < 10000:
            risk_pct = 0.05
        else:
            risk_pct = 0.08

        risk_amount = balance * risk_pct
        price_diff = abs(entry_price - stop_loss)

        if price_diff == 0:
            return 0

        units = risk_amount / price_diff

        # Confidence Adjustment
        units *= (confidence / 0.95)

        # Performance Adjustment (Learning)
        units *= self.performance_multiplier

        # Position Cap: Never exceed 1% of total balance in a single trade
        # In OANDA, 1 unit of XAU/USD is 1 ounce of gold.
        # 1% cap on "notional value" would be (balance * 0.01) / entry_price
        max_units = (balance * 0.01) / entry_price

        # NOTE: OANDA units for currencies are usually 1 unit of base currency.
        # For gold (XAU_USD), 1 unit is 1 troy ounce.
        # The prompt says: "Cap maximum position size at 1% of account balance."
        # This usually means the RISK should be capped, but the prompt says "position size".
        # I'll stick to the strict 1% of balance as notional cap if units are larger.

        units = min(units, max_units)

        return int(units) if units >= 1 else 1 # Minimum 1 unit
