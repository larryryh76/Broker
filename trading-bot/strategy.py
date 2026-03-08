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

        # Bollinger Bands for "Market Mistake" Filter
        bb = ta.bbands(df['close'], length=20, std=2)
        if bb is not None:
            df['BB_UPPER'] = bb['BBU_20_2.0']
            df['BB_LOWER'] = bb['BBL_20_2.0']

        df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)

        return df

    def generate_signal(self, df, bullish_prob, bearish_prob):
        if df is None or df.empty or 'RSI' not in df.columns:
            return "WAIT", 0

        latest = df.iloc[-1]

        # Outcome Dominance Weighted Scoring
        score_bull = 0
        score_bear = 0

        # Trend Alignment (2.0 Weight)
        if latest['close'] > latest['SMA_FAST']: score_bull += 2.0
        else: score_bear += 2.0

        # RSI Alignment (1.0 Weight)
        if latest['RSI'] < 35: score_bull += 1.0
        if latest['RSI'] > 65: score_bear += 1.0

        # AI Alignment (2.0 Weight)
        if bullish_prob > 0.60: score_bull += 2.0
        if bearish_prob > 0.60: score_bear += 2.0

        # Threshold 4.0/5.0 for execution
        if score_bull >= 4.0:
            return "BUY", score_bull
        if score_bear >= 4.0:
            return "SELL", score_bear

        return "WAIT", 0
