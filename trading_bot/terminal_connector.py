import os
import time
import MetaTrader5 as mt5
import pandas as pd
from trading_bot import config
from datetime import datetime, timedelta

class TerminalConnector:
    def __init__(self):
        self.login_id = config.MT5_LOGIN
        self.password = config.MT5_PASSWORD
        self.server = config.MT5_SERVER
        self.mt5 = mt5

    def connect(self):
        print(f"Attempting to initialize MetaTrader 5 (Native Windows Direct)...")

        path = config.TERMINAL_PATH
        if path and os.path.exists(path):
            print(f"Using terminal path: {path}")
        else:
            print("Terminal path not found or not specified. Using default discovery.")
            path = None

        try:
            # Multi-attempt initialization loop for slow startups
            # Since MT5 is pre-launched in GHA, we attempt to attach to it
            for i in range(1, 6):
                print(f"Initialization attempt {i}/5...")
                init_args = {
                    "login": int(self.login_id),
                    "password": self.password,
                    "server": self.server,
                    "timeout": 180000 # 180s
                }
                if path: init_args["path"] = path

                # Try attaching to existing terminal first
                if self.mt5.initialize(**init_args):
                    print("Attached to MetaTrader 5 successfully.")
                    break

                print(f"Attempt {i} failed: {self.mt5.last_error()}. Waiting 15s for IPC bridge readiness...")
                time.sleep(15)
            else:
                print("Direct initialization failed. Trying fallback...")
                if not self.mt5.initialize(path=path) if path else self.mt5.initialize():
                    print(f"Fallback initialization failed: {self.mt5.last_error()}")
                    return False

                if not self.mt5.login(login=int(self.login_id), password=self.password, server=self.server):
                    print(f"Login failed: {self.mt5.last_error()}")
                    return False

            print("MT5 Connected and Authorized successfully.")

            # Verify account
            info = self.mt5.account_info()
            if info is None:
                print("Failed to get account info after initialization.")
                return False

            print(f"Broker: {info.company} | Account: {info.login}")
            return True

        except Exception as e:
            print(f"TerminalConnector CRITICAL Error: {e}")
            return False

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

        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None: return None

        price = tick.ask if side == "BUY" else tick.bid

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
            "comment": "Native Bot",
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

        tick = self.mt5.symbol_info_tick(symbol)
        if tick is None: return False

        price = tick.bid if order_type == self.mt5.ORDER_TYPE_SELL else tick.ask

        request = {
            "action": self.mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot),
            "type": order_type,
            "position": ticket,
            "price": float(price),
            "deviation": 20,
            "magic": 123456,
            "comment": "Native Close",
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
        self.mt5.shutdown()
        print("MT5 shutdown.")
