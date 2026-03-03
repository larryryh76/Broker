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
    df = strat.calculate_indicators(df)

    assert "rsi" in df.columns
    assert "ma_fast" in df.columns
    assert "ma_slow" in df.columns
    assert "bb_upper" in df.columns

    signal = strat.generate_signal(df, instrument="XAUUSDm")
    print(f"Test Signal: {signal}")

    # Test position sizing
    lots = strat.calculate_position_size(5.0, instrument="XAUUSDm")
    print(f"Test Lots ($5, Gold): {lots}")
    assert lots >= 0.10

    lots_fx = strat.calculate_position_size(5.0, instrument="EURUSDm")
    print(f"Test Lots ($5, FX): {lots_fx}")
    assert lots_fx == 0.05

if __name__ == "__main__":
    test_strategy_logic()
    print("Strategy logic test passed.")
