import config

class Strategy:
    def __init__(self):
        pass

    def calculate_indicators(self, df):
        if df is None or len(df) < config.SMA_SLOW:
            return df

        # Placeholders for indicators to run without pandas_ta
        df['RSI'] = 50.0 # Neutral placeholder
        df['SMA_FAST'] = df['close'].rolling(window=config.SMA_FAST).mean()
        df['SMA_SLOW'] = df['close'].rolling(window=config.SMA_SLOW).mean()

        # MACD placeholders
        df['MACD'] = 0.0
        df['MACD_SIGNAL'] = 0.0
        df['MACD_HIST'] = 0.0

        # Bollinger Bands placeholders
        df['BB_UPPER'] = df['close'] * 1.02
        df['BB_LOWER'] = df['close'] * 0.98

        # ATR placeholder
        df['ATR'] = (df['high'] - df['low']).rolling(window=14).mean()

        # Support and Resistance Levels (Zone Detection)
        # Using a 50-period rolling window for simplified SR
        df['Support'] = df['low'].rolling(window=50).min()
        df['Resistance'] = df['high'].rolling(window=50).max()

        return df

    def generate_signal(self, df, bullish_prob, bearish_prob):
        if df is None or df.empty or 'RSI' not in df.columns:
            return "WAIT", 0

        latest = df.iloc[-1]

        # Core Conditions from Project Objectives (Simplified for Placeholder Mode)

        # 1. RSI placeholder check
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
