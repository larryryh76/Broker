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
    d1_data = [{"high": 120, "low": 80, "close": 110}]
    df_d1 = pd.DataFrame(d1_data)

    df = strat.calculate_indicators(df, df_d1=df_d1)

    assert "rsi" in df.columns
    assert "ma_fast" in df.columns
    assert "ma_slow" in df.columns
    assert "bb_upper" in df.columns

    signal = strat.generate_signal(df, instrument="XAUUSDm")
    print(f"Test Signal: {signal}")

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
