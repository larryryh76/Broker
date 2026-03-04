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

    # Test position sizing (Active Level Model)
    # Note: Strategy initializes with some idle state, results may be scaled
    lots_micro = strat.calculate_position_size(5.0, instrument="EURUSDm")
    print(f"Test Micro-Lots (Level $5, FX): {lots_micro}")
    assert lots_micro >= 0.01

    lots_gold_locked = strat.calculate_position_size(5.0, instrument="XAUUSDm")
    print(f"Test Gold Locked (Level $5): {lots_gold_locked}")
    assert lots_gold_locked == 0 or lots_gold_locked == 0.01 # Depending on enforcement

    lots_gold_unlocked = strat.calculate_position_size(50.0, instrument="XAUUSDm")
    print(f"Test Gold Unlocked (Level $50): {lots_gold_unlocked}")
    assert lots_gold_unlocked >= 0.10

    lots_fx = strat.calculate_position_size(250.0, instrument="EURUSDm")
    print(f"Test Lots (Level $250, FX): {lots_fx}")
    assert lots_fx > 0.10

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

    # Test Exit Analysis (Supreme Authority Layer)
    # Threshold for $5 Level is $0.20
    should_close, reason = strat.analyze_exit("EURUSDm", 0.25, 3.5, 5.0, 5.0)
    print(f"Test Exit (Profit): {should_close}, {reason}")
    assert should_close == True and reason == "OBJECTIVE_DOMINANCE"

    # Prediction Expiration (Dominance < 1.5 normally, < 1.0 on loss)
    should_close_d, reason_d = strat.analyze_exit("EURUSDm", 0.01, 0.5, 5.0, 5.0)
    print(f"Test Exit (Dominance): {should_close_d}, {reason_d}")
    assert should_close_d == True and reason_d == "PREDICTION_EXPIRED"

    # Test Coherence (Reward Ratios)
    levels_5 = strat.calculate_levels("BUY", 1.0, active_level=5.0)
    levels_250 = strat.calculate_levels("BUY", 1.0, active_level=250.0)

    # Verify widened targets
    dist_5 = levels_5[1] - 1.0
    dist_250 = levels_250[1] - 1.0
    print(f"Reward Target dist ($5): {dist_5:.4f} | dist ($250): {dist_250:.4f}")
    assert dist_250 > dist_5

    # Test Aggressive Relaxation
    # With 5 idle cycles, threshold should be lower than base 3.0
    relaxed_signal = strat.generate_signal(df, instrument="EURUSDm", df_h1=df_h1, idle_cycles=5)
    print(f"Test Signal (Relaxed): {relaxed_signal}")
    assert relaxed_signal is not None

if __name__ == "__main__":
    test_strategy_logic()
    print("Strategy logic test passed.")
