import os
import time
import psutil
import subprocess
import MetaTrader5 as mt5
import pandas as pd
from trading_bot import config
from datetime import datetime, timedelta
import multiprocessing

def _mt5_init_worker(args, result_queue):
    """Worker function for multiprocessing initialization."""
    try:
        success = mt5.initialize(**args)
        result_queue.put(success)
    except Exception as e:
        result_queue.put(e)

class TerminalConnector:
    def __init__(self):
        self.login_id = config.MT5_LOGIN
        self.password = config.MT5_PASSWORD
        self.server = config.MT5_SERVER
        self.mt5 = mt5

    def kill_mt5(self):
        """Forcefully terminates all MT5 processes."""
        print("MT5 MACHINE: Terminating all MT5 processes...")
        subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe", "/T"], capture_output=True)
        time.sleep(2)
        print("MT5 MACHINE: All MT5 processes terminated.")

    def launch_mt5(self, path):
        """Launches MT5 via PowerShell."""
        print(f"MT5 MACHINE: Launching MT5 from {path}...")
        # Using Start-Process to keep it in background correctly
        cmd = f'Start-Process "{path}" -ArgumentList "/portable", "/skipupdate"'
        subprocess.run(["powershell", "-Command", cmd], check=True)

        # Verify process
        time.sleep(5)
        for proc in psutil.process_iter(['name', 'pid']):
            if "terminal64.exe" in proc.info['name'].lower():
                print(f"MT5 MACHINE: MT5 Launched successfully (PID: {proc.info['pid']})")
                return True
        return False

    def connect(self):
        print(f"MT5 MACHINE: Initiating high-priority DETERMINISTIC connection sequence...")

        path = config.TERMINAL_PATH
        if not path or not os.path.exists(path):
            print(f"MT5 MACHINE: CRITICAL - Terminal path invalid: {path}")
            return False

        max_attempts = 5
        for i in range(1, max_attempts + 1):
            print(f"\n--- MT5 CONNECTION ATTEMPT {i}/{max_attempts} ---")

            # 1. Clean Slate
            self.kill_mt5()

            # 2. Fresh Launch
            if not self.launch_mt5(path):
                print(f"MT5 MACHINE: Launch failed in attempt {i}. Retrying...")
                continue

            # 3. Stabilization Wait
            print("MT5 MACHINE: Stabilization period (25s)...")
            time.sleep(25)

            # 4. Timed Initialization
            print(f"MT5 MACHINE: Attempting timed initialization to {self.server}...")

            init_args = {
                "path": path,
                "login": int(self.login_id),
                "password": self.password,
                "server": self.server,
                "timeout": 10000 # 10s library timeout
            }

            result_queue = multiprocessing.Queue()
            process = multiprocessing.Process(target=_mt5_init_worker, args=(init_args, result_queue))
            process.start()

            # Wait for 20 seconds max
            process.join(timeout=20)

            if process.is_alive():
                print("MT5 MACHINE: CRITICAL - initialization HANG detected. Killing process.")
                process.terminate()
                process.join()
                continue

            if result_queue.empty():
                print("MT5 MACHINE: Initialization failed with no result.")
                continue

            res = result_queue.get()
            if isinstance(res, Exception):
                print(f"MT5 MACHINE: Initialization exception: {res}")
                continue

            if res:
                print("MT5 MACHINE: initialize() returned True.")
                # 5. Final Verification
                info = self.mt5.account_info()
                if info:
                    print(f"MT5 MACHINE: LOGIN SUCCESS | Account: {info.login} | Balance: ${info.balance} | Server: {info.server}")
                    return True
                else:
                    err_code, err_msg = self.mt5.last_error()
                    print(f"MT5 MACHINE: account_info() returned None. Error ({err_code}): {err_msg}")
            else:
                err_code, err_msg = self.mt5.last_error()
                print(f"MT5 MACHINE: initialize() returned False. Error ({err_code}): {err_msg}")

        print("\nMT5 MACHINE: MT5 INIT FAILED AFTER CONTROLLED RETRIES.")
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
