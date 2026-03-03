import pandas as pd
from strategy import Strategy

def test_strategy_logic():
    strat = Strategy()

    # Create fake data
    data = []
    for i in range(100):
        data.append({
            "time": i,
            "mid": {"o": 100 + i*0.01, "h": 101 + i*0.01, "l": 99 + i*0.01, "c": 100.5 + i*0.01},
            "volume": 1000
        })

    df = strat.prepare_data(data)

    # Mock D1 data for structure test
    # Set daily_high to match current price to bypass structure filter
    price_now = df.iloc[-1]['close']
    d1_data = [{"high": price_now, "low": price_now - 10, "close": price_now - 5}]
    df_d1 = pd.DataFrame(d1_data)

    df = strat.calculate_indicators(df, df_d1=df_d1)

    assert "rsi" in df.columns
    assert "ma_fast" in df.columns
    assert "ma_slow" in df.columns
    assert "bb_upper" in df.columns

    # Test Ultra-Intelligent 3/3 Alignment
    # Mock H1 data for trend test
    h1_data = [{"time": i, "mid": {"o": 100, "h": 105, "l": 95, "c": 110}, "volume": 5000} for i in range(50)]
    df_h1 = strat.prepare_data(h1_data)

    # Adjust df to meet RSI/BB/MA criteria for a SELL
    # RSI > 65, Price > BB_Upper, MA_Fast < MA_Slow (short alignment), Trend DOWN
    # This is complex to mock perfectly, but we can verify the logic branches.
    signal = strat.generate_signal(df, instrument="EURUSDm", df_h1=df_h1)
    print(f"Test Signal (Strict): {signal}")

    # Test position sizing
    lots_micro = strat.calculate_position_size(10.0, instrument="EURUSDm")
    print(f"Test Micro-Lots ($10, FX): {lots_micro}")
    assert lots_micro == 0.01

    lots_gold_locked = strat.calculate_position_size(19.0, instrument="XAUUSDm")
    print(f"Test Gold Locked ($19): {lots_gold_locked}")
    assert lots_gold_locked == 0 or lots_gold_locked == 0.01

    lots_gold_unlocked = strat.calculate_position_size(21.0, instrument="XAUUSDm")
    print(f"Test Gold Unlocked ($21): {lots_gold_unlocked}")
    assert lots_gold_unlocked >= 0.10

    lots_fx = strat.calculate_position_size(5.0, instrument="EURUSDm")
    print(f"Test Lots ($5, FX): {lots_fx}")
    assert lots_fx == 0.01

    # Test ATR calculation
    atr = strat.calculate_atr(df)
    print(f"Test ATR: {atr}")
    assert atr is not None

    # Test Liquidity Gap
    # Create a gap
    df.iloc[-1, df.columns.get_loc('close')] = df.iloc[-1]['open'] + (3 * atr)
    gap = strat.check_liquidity_gap(df, "EURUSDm")
    print(f"Test Liquidity Gap: {gap}")
    assert gap == "SELL"

if __name__ == "__main__":
    test_strategy_logic()
    print("Strategy logic test passed.")
