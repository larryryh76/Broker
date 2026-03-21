import pandas as pd
import numpy as np
from trading_bot import config

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

        # Support and Resistance Levels
        df['Support'] = df['low'].rolling(window=50).min()
        df['Resistance'] = df['high'].rolling(window=50).max()

        return df

    def generate_signal(self, df, bullish_prob, bearish_prob, symbol="UNKNOWN"):
        if df is None or df.empty or 'RSI' not in df.columns:
            return "WAIT", 0

        latest = df.iloc[-1]

        # 🔥 Gold Sniper Logic: RSI Divergence + ATR Volatility
        if symbol == "XAUUSD":
            # ATR check: Wait for ATR expansion (volatility boost)
            atr_ma = df['ATR'].rolling(window=20).mean().iloc[-1]
            vol_boost = latest['ATR'] > (atr_ma * 1.1)

            # Simple RSI Divergence Check
            rsi_oversold = latest['RSI'] < 30
            rsi_overbought = latest['RSI'] > 70

            # AI Confirmation + Divergence Context
            if rsi_oversold and bullish_prob > 0.8 and vol_boost:
                return "BUY", 10
            if rsi_overbought and bearish_prob > 0.8 and vol_boost:
                return "SELL", 10
            return "WAIT", 0

        # Core Conditions for other symbols
        rsi_buy = latest['RSI'] < config.RSI_OVERSOLD
        rsi_sell = latest['RSI'] > config.RSI_OVERBOUGHT

        trend_buy = latest['close'] > latest['SMA_SLOW']
        trend_sell = latest['close'] < latest['SMA_SLOW']

        ai_buy = bullish_prob > 0.65
        ai_sell = bearish_prob > 0.65

        # Momentum confirmation
        momentum_buy = latest['SMA_FAST'] > latest['SMA_SLOW']
        momentum_sell = latest['SMA_FAST'] < latest['SMA_SLOW']

        # Weighted Scoring
        score_bull = (2.0 if trend_buy else 0) + (1.5 if rsi_buy else 0) + (2.0 if ai_buy else 0) + (0.5 if momentum_buy else 0)
        score_bear = (2.0 if trend_sell else 0) + (1.5 if rsi_sell else 0) + (2.0 if ai_sell else 0) + (0.5 if momentum_sell else 0)

        # Threshold for execution: 4.5 (Requires AI) or 4.0 (Strong Technicals)
        if score_bull >= 3.5:
            return "BUY", score_bull
        if score_bear >= 3.5:
            return "SELL", score_bear

        return "WAIT", 0
