import pandas as pd
import numpy as np

class BacktestEngine:
    def __init__(self, data):
        # data is a dict {symbol: df}
        self.data = data

    def run_backtest(self, strategy_params, ai_model):
        results = []

        for symbol, df in self.data.items():
            df = df.copy()
            # Calculate indicators using pandas rolling (avoiding pandas_ta)
            df['RSI'] = 50.0 # Placeholder
            df['SMA_FAST'] = df['close'].rolling(window=strategy_params['sma_fast']).mean()
            df['SMA_SLOW'] = df['close'].rolling(window=strategy_params['sma_slow']).mean()
            df['ATR'] = (df['high'] - df['low']).rolling(window=14).mean()

            # Simplified simulation
            # We don't have full tick data, so we simulate at close
            df = df.dropna()
            if df.empty: continue

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
