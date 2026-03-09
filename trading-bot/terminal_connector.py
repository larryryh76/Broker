import os
import time
import subprocess
import MetaTrader5 as mt5
import pandas as pd
import config
import psutil
from datetime import datetime, timedelta

class TerminalConnector:
    def __init__(self):
        self.login = config.MT5_LOGIN
        self.password = config.MT5_PASSWORD
        self.server = config.MT5_SERVER
        # Standardize path for Windows shell
        self.path = os.path.abspath(os.path.join(config.TERMINAL_DIR, "terminal64.exe")).replace("/", "\\")
        self.config_path = os.path.abspath(os.path.join(config.TERMINAL_DIR, "config", "terminal.ini")).replace("/", "\\")

    def connect(self):
        # 1. Kill any existing MT5
        for p in psutil.process_iter(['name']):
            if "terminal64.exe" in p.info['name'].lower():
                try:
                    p.kill()
                except:
                    pass
        time.sleep(5)

        # 2. SECTION 4 — MT5 Initialization (Launch before Python initializes)
        print(f"Launching MT5 Terminal: {self.path}")
        try:
            subprocess.Popen(
                [self.path, "/portable", "/skipupdate"],
                shell=False
            )
            print("Waiting 60 seconds for terminal startup...")
            time.sleep(60)
        except Exception as e:
            print(f"Launch error: {e}")
            return False

        # 3. SECTION 9 — Reliability Improvements (Retry 3 times)
        for attempt in range(1, 4):
            print(f"MT5 Initialization Attempt {attempt}/3...")
            # SECTION 4 — initialize with path
            if mt5.initialize(path=self.path, portable=True):
                print("MT5 library initialized.")

                # SECTION 5 — Login Automatically
                print("Logging in to broker...")
                if mt5.login(
                    login=int(self.login),
                    password=self.password,
                    server=self.server
                ):
                    print("Login successful.")
                    return True
                else:
                    print(f"Login failed: {mt5.last_error()}")
                    mt5.shutdown()
            else:
                print(f"Initialize failed: {mt5.last_error()}")

            if attempt < 3:
                print("Waiting 20s before retry...")
                time.sleep(20)

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

        # SECTION 9 — Retry trade execution
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
        print("MT5 shutdown complete.")
