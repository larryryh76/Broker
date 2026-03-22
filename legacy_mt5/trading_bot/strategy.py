import pandas as pd
import numpy as np
from legacy_mt5.trading_bot import config

class Strategy:
    def __init__(self):
        pass

    def calculate_indicators(self, df):
        if df is None or len(df) < config.SMA_SLOW:
            return df

        # RSI Calculation (Native Pandas)
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=config.RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=config.RSI_PERIOD).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))

        # Moving Averages
        df['SMA_FAST'] = df['close'].rolling(window=config.SMA_FAST).mean()
        df['SMA_SLOW'] = df['close'].rolling(window=config.SMA_SLOW).mean()

        # ATR Calculation (Native Pandas)
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = np.max(ranges, axis=1)
        df['ATR'] = true_range.rolling(14).mean()

        return df

    def generate_signal(self, df, bullish_prob, bearish_prob, symbol="UNKNOWN"):
        if df is None or df.empty or 'RSI' not in df.columns:
            return "WAIT", 0

        latest = df.iloc[-1]

        # 🔥 Money Machine Logic (Gold M1): AI Prediction > 75%
        if symbol == "XAUUSD":
            # Probability threshold (75%) for a 20-point move
            if bullish_prob >= 0.75:
                return "BUY", bullish_prob * 10
            if bearish_prob >= 0.75:
                return "SELL", bearish_prob * 10
            return "WAIT", 0

        # Core Conditions for other symbols
        rsi_buy = latest['RSI'] < config.RSI_OVERSOLD
        rsi_sell = latest['RSI'] > config.RSI_OVERBOUGHT

        trend_buy = latest['close'] > latest['SMA_SLOW']
        trend_sell = latest['close'] < latest['SMA_SLOW']

        ai_buy = bullish_prob > 0.65
        ai_sell = bearish_prob > 0.65

        # Weighted Scoring
        score_bull = (2.0 if trend_buy else 0) + (1.5 if rsi_buy else 0) + (2.0 if ai_buy else 0)
        score_bear = (2.0 if trend_sell else 0) + (1.5 if rsi_sell else 0) + (2.0 if ai_sell else 0)

        if score_bull >= 3.5:
            return "BUY", score_bull
        if score_bear >= 3.5:
            return "SELL", score_bear

        return "WAIT", 0
