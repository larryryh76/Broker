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

    def wait_for_mt5(self):
        print("Verifying terminal process existence...")
        for _ in range(30):
            for p in psutil.process_iter(['name']):
                if "terminal64.exe" in p.info['name'].lower():
                    print("Process confirmed.")
                    return True
            time.sleep(1)
        return False

    def connect(self):
        # 1. Ensure only ONE terminal instance
        print("Cleaning up existing MT5 processes...")
        for p in psutil.process_iter(['name']):
            if "terminal64.exe" in p.info['name'].lower():
                try:
                    p.kill()
                    print(f"Killed existing process: {p.pid}")
                except:
                    pass
        time.sleep(2)

        # 2. Ensure Data Directories Exist
        dirs = ["config", "MQL5", "Profiles"]
        for d in dirs:
            os.makedirs(os.path.join(config.TERMINAL_DIR, d), exist_ok=True)

        # 3. Launch MT5 using Windows start command for desktop context
        print(f"Launching MT5 Terminal: {self.path}")
        try:
            # Using 'start' command as requested for GHA desktop session compatibility
            subprocess.Popen(
                f'start "" "{self.path}" /portable /config:"{self.config_path}"',
                shell=True
            )

            # 4. Wait for MT5 full initialization (90 seconds as requested)
            print("Waiting for MT5 full initialization (90s)...")
            time.sleep(90)

            if not self.wait_for_mt5():
                print("Error: terminal64.exe process not detected.")
                return False

        except Exception as e:
            print(f"Launch error: {e}")
            return False

        # 5. Initialize MT5 with explicit path and 10 retries
        print(f"Attaching IPC bridge: {self.path}")

        for attempt in range(1, 11):
            print(f"Connection Attempt {attempt}/10...")
            # Note: Initialize does NOT take login/pass/server if we pre-seeded terminal.ini and launched with /config
            # but we use them as fallback if the terminal is already running.
            if mt5.initialize(path=self.path, portable=True):
                info = mt5.terminal_info()
                if info is not None and info.connected:
                    print("MT5 connection successful")
                    return True
                else:
                    print("MT5 initialized but server connection pending. Retrying...")
                    mt5.shutdown()
            else:
                print(f"MT5 initialize failed: {mt5.last_error()}")

            if attempt < 10:
                print("Waiting 10s before retry...")
                time.sleep(10)

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

        result = mt5.order_send(request)

        if result and result.retcode in [mt5.TRADE_RETCODE_REJECT, 10030, 10031]:
            print(f"IOC failed. Retrying with FOK...")
            request["type_filling"] = mt5.ORDER_FILLING_FOK
            result = mt5.order_send(request)

        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return result

        print(f"Order failed: {result.retcode if result else 'No result'}")
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
        print("MT5 disconnected.")
