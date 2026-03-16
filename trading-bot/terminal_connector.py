import os
import time
from mt5linux import MetaTrader5
import pandas as pd
import config
from datetime import datetime, timedelta

class TerminalConnector:
    def __init__(self):
        self.login_id = config.MT5_LOGIN
        self.password = config.MT5_PASSWORD
        self.server = config.MT5_SERVER
        # Bridge configuration for Docker-based mt5linux
        self.mt5 = MetaTrader5(host='localhost', port=8001)

    def connect(self):
        print("Connecting to mt5linux bridge at localhost:8001...")

        # SECTION 13 — Headless Bridge Synchronization (Requested)
        try:
            from mt5linux import wait_for_bridge
            print("Using mt5linux.wait_for_bridge(timeout=90)...")
            wait_for_bridge(host='localhost', port=8001, timeout=90)
        except (ImportError, AttributeError):
            print("wait_for_bridge not found, relying on robust retry loop.")

        # SECTION 14 — Robust Synchronization & Retry Loop (Anti-ConnectionReset)
        # Attempt to connect up to 6 times with exponential backoff as requested
        max_retries = 6
        connected = False

        for attempt in range(1, max_retries + 1):
            print(f"Connection attempt {attempt}/{max_retries}...")
            try:
                # Initialize bridge
                if self.mt5.initialize():
                    print(f"Bridge initialized successfully on attempt {attempt}.")

                    # Attempt login
                    print(f"Attempting login to {self.server}...")
                    authorized = self.mt5.login(
                        login=int(self.login_id),
                        password=self.password,
                        server=self.server
                    )

                    if authorized:
                        print(f"Logged in successfully via bridge to {self.server}")
                        connected = True
                        break
                    else:
                        print(f"Login failed on attempt {attempt}. Error: {self.mt5.last_error()}")
                        self.mt5.shutdown()
                else:
                    print(f"Bridge initialization failed on attempt {attempt}.")

            except Exception as e:
                print(f"Connection error on attempt {attempt}: {e}")

            if attempt < max_retries:
                wait_time = 10 * (2 ** (attempt - 1)) # Exponential backoff: 10s, 20s, 40s...
                # Cap wait time at 60s
                wait_time = min(wait_time, 60)
                print(f"Waiting {wait_time}s before next retry...")
                time.sleep(wait_time)

        if not connected:
            print("CRITICAL: Failed to establish authorized bridge connection after all retries.")
            return False

        return True

    def map_symbol(self, symbol):
        candidates = [symbol, symbol + "m", symbol + "-mt5"]
        for candidate in candidates:
            if self.mt5.symbol_select(candidate, True):
                return candidate
        return symbol

    def get_candles(self, symbol, timeframe, count=1000):
        symbol = self.map_symbol(symbol)
        tf_map = {"M5": self.mt5.TIMEFRAME_M5, "M15": self.mt5.TIMEFRAME_M15, "H1": self.mt5.TIMEFRAME_H1}

        rates = self.mt5.copy_rates_from_pos(symbol, tf_map.get(timeframe, self.mt5.TIMEFRAME_M5), 0, count)
        if rates is None:
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_account_info(self):
        info = self.mt5.account_info()
        return info._asdict() if info else None

    def execute_order(self, symbol, side, lot, sl, tp):
        symbol = self.map_symbol(symbol)
        order_type = self.mt5.ORDER_TYPE_BUY if side == "BUY" else self.mt5.ORDER_TYPE_SELL
        price = self.mt5.symbol_info_tick(symbol).ask if side == "BUY" else self.mt5.symbol_info_tick(symbol).bid

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot),
            "type": order_type,
            "price": float(price),
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": 123456,
            "comment": "Foundation Bot",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }

        result = self.mt5.order_send(request)
        return result

    def get_open_positions(self):
        positions = self.mt5.positions_get(magic=123456)
        return [p._asdict() for p in positions] if positions else []

    def modify_sl(self, ticket, new_sl, tp):
        request = {
            "action": self.mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": float(new_sl),
            "tp": float(tp)
        }
        return self.mt5.order_send(request)

    def close_position(self, ticket):
        pos = self.mt5.positions_get(ticket=ticket)
        if not pos: return False
        p = pos[0]
        symbol = p.symbol
        lot = p.volume
        order_type = self.mt5.ORDER_TYPE_SELL if p.type == self.mt5.POSITION_TYPE_BUY else self.mt5.ORDER_TYPE_BUY
        price = self.mt5.symbol_info_tick(symbol).bid if order_type == self.mt5.ORDER_TYPE_SELL else self.mt5.symbol_info_tick(symbol).ask

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot),
            "type": order_type,
            "position": ticket,
            "price": float(price),
            "deviation": 20,
            "magic": 123456,
            "comment": "Foundation Close",
            "type_time": self.mt5.ORDER_TIME_GTC,
            "type_filling": self.mt5.ORDER_FILLING_IOC,
        }
        return self.mt5.order_send(request)

    def get_closed_deals(self):
        from_date = datetime.now() - timedelta(hours=24)
        deals = self.mt5.history_deals_get(from_date, datetime.now())
        if deals is None: return []
        return [d._asdict() for d in deals if d.magic == 123456]

    def disconnect(self):
        # SECTION 7 — Safe Shutdown
        self.mt5.shutdown()
        print("MT5 foundation shutdown.")
