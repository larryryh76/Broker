import os
import time
import subprocess
import MetaTrader5 as mt5
import pandas as pd
import config

class TerminalConnector:
    def __init__(self):
        self.login = config.MT5_LOGIN
        self.password = config.MT5_PASSWORD
        self.server = config.MT5_SERVER
        self.path = os.path.join(config.TERMINAL_DIR, "terminal64.exe")

    def connect(self):
        # 1. Clean slate: Kill any zombie processes
        if os.name == 'nt':
            print("Cleaning up existing MT5 processes...")
            os.system('taskkill /f /im terminal64.exe /t >nul 2>&1')
            time.sleep(2)

        # 2. Pre-launch terminal process explicitly for GHA/Headless stability
        # This ensures the terminal is running before the library attempts to attach.
        if os.path.exists(self.path):
            print(f"Pre-launching MT5 Terminal: {self.path}")
            try:
                subprocess.Popen([self.path, "/portable"])
                print("Terminal process launched. Waiting 20 seconds for boot...")
                time.sleep(20)
            except Exception as e:
                print(f"Failed to launch terminal process: {e}")
        else:
            print(f"Warning: Terminal executable not found at {self.path}. Assuming standard installation.")

        # 3. Robust initialization retry loop
        max_attempts = 5
        retry_delay = 10

        for attempt in range(1, max_attempts + 1):
            print(f"MT5 Connection Attempt {attempt}/{max_attempts}...")

            # Use credentials directly in initialize to bypass handshake timeouts
            success = mt5.initialize(
                path=self.path,
                login=self.login,
                password=self.password,
                server=self.server,
                portable=True,
                timeout=60000
            )

            if success:
                print("MONEY MACHINE CONNECTED. IPC BRIDGE ACTIVE.")
                # Extra verification: check terminal info
                info = mt5.terminal_info()
                if info:
                    print(f"Terminal connection verified. Connected: {info.connected}")
                return True
            else:
                error = mt5.last_error()
                print(f"MT5 Init failed (Attempt {attempt}): {error}")
                if attempt < max_attempts:
                    print(f"Waiting {retry_delay}s before retry...")
                    time.sleep(retry_delay)

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
            "comment": "Money Machine Exec",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        # RETRY WITH FOK IF IOC FAILS
        if result and result.retcode in [mt5.TRADE_RETCODE_REJECT, 10030, 10031]:
            print(f"IOC filling failed (Retcode {result.retcode}). Retrying with FOK...")
            request["type_filling"] = mt5.ORDER_FILLING_FOK
            result = mt5.order_send(request)

        if result and result.retcode == mt5.TRADE_RETCODE_DONE:
            return result

        print(f"Order failed: {result.retcode if result else 'No result'} | Comment: {result.comment if result else ''}")
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

    def disconnect(self):
        mt5.shutdown()
        print("MT5 Disconnected.")
