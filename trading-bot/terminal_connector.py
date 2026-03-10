import os
import time
import MetaTrader5 as mt5
import pandas as pd
import config
from datetime import datetime, timedelta

class TerminalConnector:
    def __init__(self):
        self.login_id = config.MT5_LOGIN
        self.password = config.MT5_PASSWORD
        self.server = config.MT5_SERVER
        # Windows-style path as expected by the MetaTrader5 library running under Wine
        self.path = r"C:\Program Files\MetaTrader 5\terminal64.exe"

    def connect(self):
        # SUPREME AUTHORITY LAYER: Connection Retry
        for attempt in range(5):
            print(f"MT5 Wine/GUI connection attempt {attempt+1}/5")

            # Initialize MT5 using the Windows path within the Wine environment
            if mt5.initialize(
                path=self.path,
                portable=True,
                timeout=120000
            ):
                print("MT5 IPC connection established within Linux Wine session")

                # Perform login separately after successful initialization
                print(f"Authorizing account {self.login_id} on {self.server}...")
                authorized = mt5.login(
                    login=int(self.login_id),
                    password=self.password,
                    server=self.server
                )

                if authorized:
                    print(f"MT5 session fully authorized")
                    return True
                else:
                    print(f"MT5 authorization failed: {mt5.last_error()}")
                    mt5.shutdown()
            else:
                print("IPC initialization failed (Linux/Wine mismatch):", mt5.last_error())

            time.sleep(15)

        return False

    def map_symbol(self, symbol):
        candidates = [symbol, symbol + "m", symbol + "-mt5"]
        for candidate in candidates:
            if mt5.symbol_select(candidate, True):
                return candidate
        return symbol

    def get_candles(self, symbol, timeframe, count=1000):
        symbol = self.map_symbol(symbol)
        tf_map = {"M5": mt5.TIMEFRAME_M5, "M15": mt5.TIMEFRAME_M15, "H1": mt5.TIMEFRAME_H1}

        rates = mt5.copy_rates_from_pos(symbol, tf_map.get(timeframe, mt5.TIMEFRAME_M5), 0, count)
        if rates is None:
            return None

        df = pd.DataFrame(rates)
        df['time'] = pd.to_datetime(df['time'], unit='s')
        return df

    def get_account_info(self):
        info = mt5.account_info()
        return info._asdict() if info else None

    def execute_order(self, symbol, side, lot, sl, tp):
        symbol = self.map_symbol(symbol)
        order_type = mt5.ORDER_TYPE_BUY if side == "BUY" else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(symbol).ask if side == "BUY" else mt5.symbol_info_tick(symbol).bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot),
            "type": order_type,
            "price": float(price),
            "sl": float(sl),
            "tp": float(tp),
            "deviation": 20,
            "magic": 123456,
            "comment": "Money Machine Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        # Retry trade execution if needed
        for i in range(3):
            result = mt5.order_send(request)
            if result and result.retcode == mt5.TRADE_RETCODE_DONE:
                return result
            print(f"Execution failed (Attempt {i+1}/3): {result.comment if result else 'No result'}")
            time.sleep(2)

        return None

    def get_open_positions(self):
        positions = mt5.positions_get(magic=123456)
        return [p._asdict() for p in positions] if positions else []

    def modify_sl(self, ticket, new_sl, tp):
        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": float(new_sl),
            "tp": float(tp)
        }
        return mt5.order_send(request)

    def close_position(self, ticket):
        pos = mt5.positions_get(ticket=ticket)
        if not pos: return False
        p = pos[0]
        symbol = p.symbol
        lot = p.volume
        order_type = mt5.ORDER_TYPE_SELL if p.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(lot),
            "type": order_type,
            "position": ticket,
            "price": float(price),
            "deviation": 20,
            "magic": 123456,
            "comment": "Money Machine Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }
        return mt5.order_send(request)

    def get_closed_deals(self):
        from_date = datetime.now() - timedelta(hours=24)
        deals = mt5.history_deals_get(from_date, datetime.now())
        if deals is None: return []
        return [d._asdict() for d in deals if d.magic == 123456]

    def disconnect(self):
        mt5.shutdown()
        print("MT5 session closed.")
