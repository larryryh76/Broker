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

    def calculate_atr(self, df, length=14):
        if df is None or len(df) < length:
            return None
        atr = ta.atr(df["high"], df["low"], df["close"], length=length)
        return atr.iloc[-1] if atr is not None else None

    def calculate_indicators(self, df):
        if df is None or len(df) < 50:
            return None

        # RSI 7 (Increased Sensitivity)
        df["rsi"] = ta.rsi(df["close"], length=7)

        # Moving Averages: 20-period fast and 50-period slow
        df["ma_fast"] = ta.sma(df["close"], length=20)
        df["ma_slow"] = ta.sma(df["close"], length=50)

        # Bollinger Bands (Extreme Deviation Detection)
        bb = ta.bbands(df["close"], length=20, std=2)
        # Use standard column names provided by pandas_ta
        df["bb_upper"] = bb.iloc[:, 2] # BBU
        df["bb_lower"] = bb.iloc[:, 0] # BBL

        return df

    def check_market_mistake(self, df, instrument):
        """
        Market Mistake Filter:
        If price is > 100 points away from MA_FAST, it's a mistake/overextension.
        Execute instant reversal.
        """
        if df is None or len(df) < 2:
            return None

        latest = df.iloc[-1]
        dist = abs(latest["close"] - latest["ma_fast"])

        # Threshold: 100 points (Gold: $1.00, FX: 10 pips)
        threshold = 1.00 if "XAU" in instrument else 0.001

        if dist > threshold:
            if latest["close"] > latest["ma_fast"]:
                return "SELL" # Reversal from overbought
            else:
                return "BUY" # Reversal from oversold
        return None

    def generate_signal(self, df, instrument=""):
        """
        Hyper-Aggressive Signal: RSI 7 + BB + MA
        """
        if df is None or len(df) < 50:
            return None

        latest = df.iloc[-1]

        # Market Mistake Check (Highest Priority)
        mistake_side = self.check_market_mistake(df, instrument)
        if mistake_side:
            return {"side": mistake_side, "confidence": 0.95, "price": latest["close"], "reason": "MARKET_MISTAKE"}

        # 1. RSI Sensitivity (Aggressive)
        rsi_long = latest["rsi"] < 40
        rsi_short = latest["rsi"] > 60

        # 2. Moving Average Alignment
        ma_aligned_long = latest["ma_fast"] > latest["ma_slow"]
        ma_aligned_short = latest["ma_fast"] < latest["ma_slow"]

        # 3. Bollinger Band Touch
        bb_long = latest["close"] <= latest["bb_lower"]
        bb_short = latest["close"] >= latest["bb_upper"]

        if (rsi_long or bb_long) and ma_aligned_long:
            return {"side": "BUY", "confidence": 0.85, "price": latest["close"]}
        elif (rsi_short or bb_short) and ma_aligned_short:
            return {"side": "SELL", "confidence": 0.85, "price": latest["close"]}

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

    def calculate_position_size(self, balance, instrument="", target=50.0):
        """
        Aggressive Quest Scaling:
        Base: $5 -> 0.05 lots
        Phase 1 Optimization:
        - Strict 0.01 lots until Virtual Equity > $15.00
        - Gold Unlock only after Virtual Equity >= $20.00
        """
        # Micro-Lot Enforcement
        if balance <= 15.00:
            return 0.01

        if "XAU" in instrument:
            # Gold Unlock Check
            if balance < 20.00:
                return 0 # Locked

            if balance < 50:
                # Gold Override for aggressive Phase 1
                lots = 0.10 + (balance / 50.0) * 0.40
            else:
                lots = (balance / 5.0) * 0.05
        else:
            lots = (balance / 5.0) * 0.05

        lots = max(0.01, round(lots, 2))

        # Safety Cap
        lots = min(lots, 100.0)

        return lots
