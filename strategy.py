import pandas as pd
import pandas_ta as ta
from config import logger, RISK_REWARD_RATIO

class Strategy:
    def __init__(self):
        self.win_rate_threshold = 0.50
        self.performance_multiplier = 1.0
        self.idle_multiplier = 1.0
        self._consecutive_losses = 0

    def adjust_for_loss(self, consecutive_losses):
        """Loss Intelligence Update: After 2 consecutive losses, increase probability-weighted risk."""
        self._consecutive_losses = consecutive_losses
        if consecutive_losses >= 2:
            logger.info(f"LOSS INTELLIGENCE Active ({consecutive_losses} losses): Increasing risk profile & targeting faster exits.")

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

    def get_h1_trend(self, df_h1):
        """
        Trend Alignment Filter:
        Returns 'UP' if price is above H1 SMA 20, 'DOWN' if below.
        """
        if df_h1 is None or len(df_h1) < 20:
            return "UNKNOWN"

        latest = df_h1.iloc[-1]
        sma_20 = ta.sma(df_h1["close"], length=20).iloc[-1]

        if latest["close"] > sma_20:
            return "UP"
        elif latest["close"] < sma_20:
            return "DOWN"
        return "NEUTRAL"

    def calculate_indicators(self, df, df_d1=None):
        if df is None or len(df) < 50:
            return None

        # Market Structure: Daily High, Low, and Pivots
        if df_d1 is not None and len(df_d1) >= 1:
            yesterday = df_d1.iloc[-1]
            high = yesterday["high"]
            low = yesterday["low"]
            close = yesterday["close"]

            # Standard Pivot Points
            pivot = (high + low + close) / 3
            r1 = (2 * pivot) - low
            s1 = (2 * pivot) - high

            df["daily_high"] = high
            df["daily_low"] = low
            df["pivot"] = pivot
            df["r1"] = r1
            df["s1"] = s1

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

    def check_liquidity_gap(self, df, instrument):
        """
        Liquidity Gap Filter:
        If price moves > 2x 14-period ATR in 5 minutes (current candle),
        trigger a mean-reversion trade. (EURUSDm and GBPJPYm focus)
        """
        if df is None or len(df) < 15:
            return None

        if "EURUSD" not in instrument and "GBPJPY" not in instrument:
            return None

        latest = df.iloc[-1]
        atr = self.calculate_atr(df, length=14)
        if not atr:
            return None

        move = abs(latest["close"] - latest["open"])
        if move > (2 * atr):
            # Mean-reversion
            return "SELL" if latest["close"] > latest["open"] else "BUY"
        return None

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

    def generate_signal(self, df, instrument="", df_h1=None, idle_cycles=0, realized_pnl=0, daily_target=50.0):
        """
        Decision Authority Model: Outcome Dominance & Decisiveness
        Incremental relaxation of thresholds based on inactivity (idle_cycles).
        """
        if df is None or len(df) < 50:
            return None

        latest = df.iloc[-1]

        # Liquidity Gap Check (Mean Reversion)
        gap_side = self.check_liquidity_gap(df, instrument)
        if gap_side:
            return {"side": gap_side, "confidence": 0.95, "price": latest["close"], "reason": "LIQUIDITY_GAP"}

        # Market Structure Check (REQUIRED)
        structure_levels = ["daily_high", "daily_low", "pivot", "r1", "s1"]
        near_structure = False
        buffer = 1.00 if "XAU" in instrument else 0.0010
        for level in structure_levels:
            if level in latest and abs(latest["close"] - latest[level]) <= buffer:
                near_structure = True
                break

        if not near_structure:
            return {"side": "SKIP", "confidence": 0, "price": latest["close"], "reason": "NOT_NEAR_STRUCTURE"}

        # Market Mistake Check (Highest Priority)
        mistake_side = self.check_market_mistake(df, instrument)
        if mistake_side:
            return {"side": mistake_side, "confidence": 0.95, "price": latest["close"], "reason": "MARKET_MISTAKE"}

        # Directional Factor Weights (Outcome Dominance Model)
        WEIGHT_TREND = 2.0  # Intelligence Priority
        WEIGHT_RSI = 1.0
        WEIGHT_BB = 1.0
        WEIGHT_MA = 1.0

        dominance_buy = 0.0
        dominance_sell = 0.0

        # 1. RSI (Boundary Analysis)
        if latest["rsi"] < 35: dominance_buy += WEIGHT_RSI
        if latest["rsi"] > 65: dominance_sell += WEIGHT_RSI

        # 2. Moving Average Alignment (Momentum Analysis)
        if latest["ma_fast"] > latest["ma_slow"]: dominance_buy += WEIGHT_MA
        if latest["ma_fast"] < latest["ma_slow"]: dominance_sell += WEIGHT_MA

        # 3. Bollinger Band Touch (Exhaustion)
        if latest["close"] <= latest["bb_lower"]: dominance_buy += WEIGHT_BB
        if latest["close"] >= latest["bb_upper"]: dominance_sell += WEIGHT_BB

        # 4. Trend Alignment (Systemic Intelligence)
        trend = self.get_h1_trend(df_h1) if df_h1 is not None else "UNKNOWN"
        if trend == "UP" or trend == "UNKNOWN": dominance_buy += WEIGHT_TREND
        if trend == "DOWN" or trend == "UNKNOWN": dominance_sell += WEIGHT_TREND

        # Outcome Dominance Decision Authority
        # BASE Threshold: 3.0 out of 5.0 (Clear Superiority)
        # Incremental Relaxation: Decrease threshold as idle_cycles increase
        base_threshold = 3.0

        # Incremental relaxation (0.2 reduction per cycle after 3)
        relaxation = max(0, (idle_cycles - 3) * 0.2)

        # Aggression Scaling Logic: If cumulative PnL is negative OR flat, reduce strictness
        if realized_pnl <= 0:
            relaxation += 0.5

        # LOSS INTERPRETATION: After 2 losses, stop waiting for "perfect" conditions
        if self._consecutive_losses >= 2:
            relaxation += 1.0

        threshold = max(1.5, base_threshold - relaxation)

        if idle_cycles > 0 or realized_pnl <= 0 or self._consecutive_losses >= 2:
            logger.info(f"Decision Threshold: {threshold:.2f} (Idle: {idle_cycles}, PnL: {realized_pnl:.2f}, Losses: {self._consecutive_losses})")

        # TREND & MOMENTUM PRIORITY: When uncertain, favor trend continuation
        # If one side has clear superiority but doesn't hit threshold,
        # allow execution if idle cycles are extreme or objective is unmet.
        if dominance_buy >= threshold and dominance_buy > dominance_sell:
            conf = min(0.95, dominance_buy / 5.0)
            return {"side": "BUY", "confidence": conf, "price": latest["close"]}
        elif dominance_sell >= threshold and dominance_sell > dominance_buy:
            conf = min(0.95, dominance_sell / 5.0)
            return {"side": "SELL", "confidence": conf, "price": latest["close"]}

        # MOMENTUM PRIORITY OVERRIDE
        # If bias is clear (2.0 delta) and objective unmet, favor momentum
        if realized_pnl < daily_target and abs(dominance_buy - dominance_sell) >= 2.0:
            side = "BUY" if dominance_buy > dominance_sell else "SELL"
            logger.info(f"MOMENTUM PRIORITY: Decisive Bias detected for {side}. Triggering execution.")
            return {"side": side, "confidence": 0.80, "price": latest["close"], "reason": "MOMENTUM_PRIORITY"}

        return {"side": "SKIP", "confidence": 0, "price": latest["close"]}

    def calculate_levels(self, side, price, active_level=5.0):
        """
        Capital-Objective Coherence:
        Stop Loss: 2% (widening on loss).
        Take Profit: Scales with Active Level to match exponential objectives.
        """
        risk_pct = 0.02

        # LOSS INTELLIGENCE: Increase stop distance to avoid noise
        if self._consecutive_losses >= 1:
            risk_pct = 0.03

        # CAPITAL-OBJECTIVE COHERENCE: Widen Reward as Level increases
        # Level 5: 1:3 | Level 50: 1:4 | Level 250: 1:5 ...
        import math
        reward_multiplier = 3.0 + max(0, math.log10(active_level / 5.0) * 2.0)

        if side == "BUY":
            stop_loss = price * (1 - risk_pct)
            take_profit = price + (price - stop_loss) * reward_multiplier
        elif side == "SELL":
            stop_loss = price * (1 + risk_pct)
            take_profit = price - (stop_loss - price) * reward_multiplier
        else:
            return None, None

        return stop_loss, take_profit

    def analyze_exit(self, symbol, current_profit, dominance_score, virtual_equity, active_level):
        """
        Entry-Exit Coherence:
        Exit conditions must be harder to trigger than entry.
        Profit realization has higher priority than indefinite holding.
        """
        # PROFIT AUTHORITY: Scale profit target with Active Level
        # 4% of active_level is the minimum dominance threshold for closure
        profit_threshold = active_level * 0.04

        if current_profit >= profit_threshold:
            return True, "OBJECTIVE_DOMINANCE"

        # LOSS-AGGRESSION REBALANCE: Decrease exit sensitivity after loss
        weakness_threshold = 1.5 if self._consecutive_losses == 0 else 1.0

        # Exit if dominance falls below threshold (weakened prediction)
        if dominance_score < weakness_threshold:
            return True, "PREDICTION_EXPIRED"

        return False, None

    def calculate_position_size(self, active_level, instrument="", target=50.0, idle_cycles=0, realized_pnl=0):
        """
        Aggressive Quest Scaling & Multiplier Escalation:
        - Multiplier must NOT remain fixed at 1.0 during inactivity.
        - Increment Multiplier gradually (1.2 -> 1.4 -> 1.6...)
        """
        # Multiplier Escalation Logic (mandatory during inactivity)
        self.idle_multiplier = 1.0 + (idle_cycles * 0.2)

        # AGGRESSION SCALING: If negative/flat, increase size progressively
        if realized_pnl <= 0:
            self.idle_multiplier += 0.5

        self.idle_multiplier = min(5.0, self.idle_multiplier) # Increased cap for profit pursuit

        if "XAU" in instrument:
            # Gold Unlock Check (Promotion level required)
            if active_level < 50.00:
                return 0 # Locked

        # ANTI-FREEZE: Never stop trading entirely. Reduce size if confidence low (implied by active_level)

        # Micro-Lot Enforcement for Bootstrap Level
        if active_level < 50.00:
            # Escalated micro-sizing for Phase 1
            lots = 0.01 * self.idle_multiplier
            return round(lots, 2)

        if "XAU" in instrument:
            # Gold Unlock Check (Promotion level required)
            if active_level < 50.00:
                return 0 # Locked

            if active_level < 250:
                # Gold Override for aggressive Phase 1
                lots = (0.10 + (active_level / 250.0) * 0.40) * self.idle_multiplier
            else:
                lots = (active_level / 5.0) * 0.05 * self.idle_multiplier
        else:
            lots = (active_level / 5.0) * 0.05 * self.idle_multiplier

        lots = max(0.01, round(lots, 2))

        # Safety Cap
        lots = min(lots, 100.0)

        return lots
