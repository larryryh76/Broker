import pandas as pd
import pandas_ta as ta
import numpy as np

class BacktestEngine:
    def __init__(self, data):
        # data is a dict {symbol: df}
        self.data = data

    def run_backtest(self, strategy_params, ai_model):
        results = []

        for symbol, df in self.data.items():
            df = df.copy()
            # Calculate dynamic indicators based on strategy_params
            df['RSI'] = ta.rsi(df['close'], length=strategy_params['rsi_period'])
            df['SMA_FAST'] = ta.sma(df['close'], length=strategy_params['sma_fast'])
            df['SMA_SLOW'] = ta.sma(df['close'], length=strategy_params['sma_slow'])
            df['ATR'] = ta.atr(df['high'], df['low'], df['close'], length=14)

            # Simplified simulation
            # We don't have full tick data, so we simulate at close
            df = df.dropna()
            if df.empty: continue

            # Feature prep for AI prediction
            # We skip the heavy AI prediction loop for thousands of strategy backtests
            # to stay within GHA time limits. Instead, we use the trend as a proxy.

            pnl = 0
            trades = 0
            win = 0

            for i in range(len(df)-1):
                curr = df.iloc[i]
                nxt = df.iloc[i+1]

                # Signal logic using params
                buy_signal = (curr['RSI'] < strategy_params['rsi_oversold']) and (curr['close'] > curr['SMA_FAST'])
                sell_signal = (curr['RSI'] > strategy_params['rsi_overbought']) and (curr['close'] < curr['SMA_FAST'])

                if buy_signal:
                    diff = nxt['close'] - curr['close']
                    pnl += diff
                    trades += 1
                    if diff > 0: win += 1
                elif sell_signal:
                    diff = curr['close'] - nxt['close']
                    pnl += diff
                    trades += 1
                    if diff > 0: win += 1

            win_rate = (win / trades) if trades > 0 else 0
            results.append({"symbol": symbol, "pnl": pnl, "win_rate": win_rate, "trades": trades})

        # Overall score
        total_pnl = sum(r['pnl'] for r in results)
        avg_win_rate = np.mean([r['win_rate'] for r in results]) if results else 0
        total_trades = sum(r['trades'] for r in results)

        # Scoring function: PnL * WinRate (Adjusted)
        score = total_pnl * (avg_win_rate + 0.5)

        return {
            "score": score,
            "pnl": total_pnl,
            "win_rate": avg_win_rate,
            "trades": total_trades,
            "params": strategy_params
        }
