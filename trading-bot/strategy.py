import pandas_ta as ta
import config

class Strategy:
    def __init__(self):
        pass

    def calculate_indicators(self, df):
        if df is None or len(df) < config.SMA_SLOW:
            return df

        df['RSI'] = ta.rsi(df['close'], length=config.RSI_PERIOD)
        df['SMA_FAST'] = ta.sma(df['close'], length=config.SMA_FAST)
        df['SMA_SLOW'] = ta.sma(df['close'], length=config.SMA_SLOW)

        # MACD
        macd = ta.macd(df['close'])
        if macd is not None:
            df['MACD'] = macd['MACD_12_26_9']
            df['MACD_SIGNAL'] = macd['MACDs_12_26_9']
            df['MACD_HIST'] = macd['MACDh_12_26_9']

        # Bollinger Bands
        bb = ta.bbands(df['close'], length=20, std=2)
        if bb is not None:
            df['BB_UPPER'] = bb['BBU_20_2.0']
            df['BB_LOWER'] = bb['BBL_20_2.0']

        # ATR for Risk Management
        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        # Support and Resistance Levels (Zone Detection)
        # Using a 50-period rolling window for simplified SR
        df['Support'] = df['low'].rolling(window=50).min()
        df['Resistance'] = df['high'].rolling(window=50).max()

        return df

    def generate_signal(self, df, bullish_prob, bearish_prob):
        if df is None or df.empty or 'RSI' not in df.columns:
            return "WAIT", 0

        latest = df.iloc[-1]

        # Core Conditions from Project Objectives

        # 1. RSI oversold/overbought check
        rsi_buy = latest['RSI'] < config.RSI_OVERSOLD
        rsi_sell = latest['RSI'] > config.RSI_OVERBOUGHT

        # 2. Price vs Primary Trend MA (SMA_SLOW)
        trend_buy = latest['close'] > latest['SMA_SLOW']
        trend_sell = latest['close'] < latest['SMA_SLOW']

        # 3. AI Probability Threshold
        ai_buy = bullish_prob > 0.60
        ai_sell = bearish_prob > 0.60

        # 4. Momentum / SR Confirmations
        # Buy: Price near support OR MACD Hist increasing
        momentum_buy = (latest['close'] <= latest['Support'] * 1.001) or (latest['MACD_HIST'] > 0)
        # Sell: Price near resistance OR MACD Hist decreasing
        momentum_sell = (latest['close'] >= latest['Resistance'] * 0.999) or (latest['MACD_HIST'] < 0)

        # Outcome Dominance Weighted Scoring (Intelligence Layer)
        score_bull = (2.0 if trend_buy else 0) + (1.0 if rsi_buy else 0) + (2.0 if ai_buy else 0) + (0.5 if momentum_buy else 0)
        score_bear = (2.0 if trend_sell else 0) + (1.0 if rsi_sell else 0) + (2.0 if ai_sell else 0) + (0.5 if momentum_sell else 0)

        # Threshold for execution: 4.5/5.5
        if score_bull >= 4.5:
            return "BUY", score_bull
        if score_bear >= 4.5:
            return "SELL", score_bear

        return "WAIT", 0
