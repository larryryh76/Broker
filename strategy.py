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
        if df is None or len(df) < 50: # Need 50 for RSI and MAs
            return None

        latest = df.iloc[-1]
        prev = df.iloc[-2]

        # RSI Filter: BUY if RSI < 30, SELL if RSI > 70
        rsi_oversold = latest["rsi"] < 30
        rsi_overbought = latest["rsi"] > 70

        # Aggressive Signal: Current price vs Previous candle high/low
        if latest["close"] > prev["high"] and rsi_oversold:
            return {"side": "BUY", "confidence": 0.95, "price": latest["close"]}
        elif latest["close"] < prev["low"] and rsi_overbought:
            return {"side": "SELL", "confidence": 0.95, "price": latest["close"]}

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

    def calculate_position_size(self, balance, target=50.0):
        """
        Aggressive Lot Scaling:
        Lot_Size = (Current_Target / 50) * 0.1
        MAX_LOTS = 100
        """
        lots = (target / 50.0) * 0.1
        lots = max(0.01, round(lots, 2))

        # Safety Cap
        lots = min(lots, 100.0)

        return lots
