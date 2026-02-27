import pytest
import pandas as pd
from strategy import Strategy

@pytest.fixture
def strategy():
    return Strategy()

@pytest.fixture
def sample_candles():
    # 60 candles to ensure enough data for indicators
    return [
        {
            "time": f"2023-01-01T00:{i:02}:00Z",
            "mid": {"o": str(100+i), "h": str(101+i), "l": str(99+i), "c": str(100+i)},
            "volume": 100
        } for i in range(60)
    ]

def test_prepare_data(strategy, sample_candles):
    df = strategy.prepare_data(sample_candles)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 60
    assert "close" in df.columns

def test_calculate_indicators(strategy, sample_candles):
    df = strategy.prepare_data(sample_candles)
    df = strategy.calculate_indicators(df)
    assert "rsi" in df.columns
    assert "ma_fast" in df.columns
    assert "ma_slow" in df.columns
    # First 50 rows of ma_slow should be NaN
    assert pd.isna(df["ma_slow"].iloc[48])
    assert not pd.isna(df["ma_slow"].iloc[49])

def test_calculate_levels_buy(strategy):
    price = 100
    sl, tp = strategy.calculate_levels("BUY", price)
    assert sl == 98 # 2% risk
    assert tp == 106 # 1:3 RR (risk=2, reward=6)

def test_calculate_levels_sell(strategy):
    price = 100
    sl, tp = strategy.calculate_levels("SELL", price)
    assert sl == 102
    assert tp == 94

def test_calculate_position_size_small_balance(strategy):
    balance = 50
    entry = 100
    sl = 98
    confidence = 0.95
    # Risk 2% of 50 = 1.0
    # Price diff = 2
    # Units = 1.0 / 2 = 0.5
    # Confidence adj = 0.5 * (0.95/0.95) = 0.5
    # Max units = (50 * 0.01) / 100 = 0.5 / 100 = 0.005
    # Hmm, 1% cap on position size is very small for $50 balance.
    # (50 * 0.01) / 100 = 0.005 units.
    # Minimum 1 unit is returned.
    units = strategy.calculate_position_size(balance, entry, sl, confidence)
    assert units == 1

def test_generate_signal_buy(strategy):
    # Create a trend: price above MA20, MA20 above MA50, RSI oversold (artificially)
    data = []
    for i in range(60):
        # MA50 will be around 100
        # MA20 will be higher if price is increasing
        price = 100 + i
        data.append({"rsi": 20, "ma_fast": 110, "ma_slow": 100, "close": 115})

    df = pd.DataFrame(data)
    signal = strategy.generate_signal(df)
    assert signal["side"] == "BUY"
    assert signal["confidence"] == 0.85 # 3 indicators aligned
