import os
import pandas as pd
from trading_bot import config
from datetime import datetime

class DataEngine:
    def __init__(self, connector):
        self.connector = connector
        if not os.path.exists(config.DATA_DIR):
            os.makedirs(config.DATA_DIR)

    def download_data(self, symbol, timeframe, count=2000):
        print(f"Downloading {count} candles for {symbol} {timeframe}...")
        df = self.connector.get_candles(symbol, timeframe, count)
        if df is not None and not df.empty:
            filename = f"{symbol}_{timeframe}.csv"
            path = os.path.join(config.DATA_DIR, filename)
            df.to_csv(path, index=False)
            print(f"Saved to {path}")
            return df
        else:
            print(f"Failed to download data for {symbol}")
            return None

    def load_cached_data(self, symbol, timeframe):
        filename = f"{symbol}_{timeframe}.csv"
        path = os.path.join(config.DATA_DIR, filename)
        if os.path.exists(path):
            df = pd.read_csv(path)
            df['time'] = pd.to_datetime(df['time'])
            return df
        return None

    def get_all_data(self):
        data = {}
        for symbol in config.SYMBOLS:
            df = self.download_data(symbol, config.DEFAULT_TIMEFRAME)
            if df is not None:
                data[symbol] = df
        return data
