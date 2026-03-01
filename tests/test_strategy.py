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
    # Hyper-compounding logic: (50/5)*0.01 = 0.1
    lots = strategy.calculate_position_size(balance, entry, sl, confidence)
    assert lots == 0.1

def test_generate_signal_buy(strategy):
    data = [
        {"high": 100, "low": 90, "close": 95},
        {"high": 105, "low": 95, "close": 110} # close > prev high
    ]

    df = pd.DataFrame(data)
    signal = strategy.generate_signal(df)
    assert signal["side"] == "BUY"

def test_adjust_parameters_high_win_rate(strategy):
    learning_state = {"win_rate": 70, "total_trades": 10}
    strategy.adjust_parameters(learning_state)
    assert strategy.performance_multiplier == 1.2

def test_adjust_parameters_low_win_rate(strategy):
    learning_state = {"win_rate": 30, "total_trades": 10}
    strategy.adjust_parameters(learning_state)
    assert strategy.performance_multiplier == 0.8

def test_adjust_parameters_insufficient_data(strategy):
    learning_state = {"win_rate": 70, "total_trades": 5}
    strategy.adjust_parameters(learning_state)
    assert strategy.performance_multiplier == 1.0
