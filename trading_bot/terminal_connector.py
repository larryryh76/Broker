import os
import time
import psutil
import subprocess
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

    def kill_mt5(self):
        """Forcefully terminates all MT5 processes."""
        print("MT5 MACHINE: Terminating all MT5 processes...")
        subprocess.run(["taskkill", "/F", "/IM", "terminal64.exe", "/T"], capture_output=True)
        time.sleep(2)
        print("MT5 MACHINE: All MT5 processes terminated.")

    def launch_mt5(self, path):
        """Launches MT5 via PowerShell (Single Session Model)."""
        print(f"MT5 MACHINE: Launching MT5 from {path}...")

        # Using Start-Process in Normal window style for single session
        cmd = f'Start-Process "{path}" -ArgumentList "/portable", "/skipupdate" -WindowStyle Normal'
        subprocess.run(["powershell", "-Command", cmd], check=True)

        # Verify process
        time.sleep(15)
        for proc in psutil.process_iter(['name', 'pid']):
            if "terminal64.exe" in proc.info['name'].lower():
                print(f"MT5 MACHINE: MT5 Launched successfully (PID: {proc.info['pid']})")
                return True
        return False

    def discover_terminal(self):
        """Dynamically searches for terminal64.exe with strict validation."""
        # 1. Check Config Path (Passed from GHA)
        if config.TERMINAL_PATH:
            if os.path.exists(config.TERMINAL_PATH):
                print(f"MT5 MACHINE: Verified Terminal path from config: {config.TERMINAL_PATH}")
                return config.TERMINAL_PATH
            else:
                print(f"MT5 MACHINE: WARNING - Config path does not exist: {config.TERMINAL_PATH}")

        print("MT5 MACHINE: Searching dynamically for terminal64.exe...")
        # 2. Search common drive roots (Shallow search first for performance)
        drives = ["C:\\", "D:\\"]
        for drive in drives:
            if not os.path.exists(drive): continue
            # Look in typical GHA install locations first
            common_subdirs = ["mt5_terminal", "Program Files", "Program Files (x86)"]
            for sd in common_subdirs:
                full_sd = os.path.join(drive, sd)
                if not os.path.exists(full_sd): continue
                for root, dirs, files in os.walk(full_sd):
                    if "terminal64.exe" in files:
                        found_path = os.path.join(root, "terminal64.exe")
                        print(f"MT5 MACHINE: Dynamic Discovery SUCCESS: {found_path}")
                        return found_path

        return None

    def connect(self):
        print(f"MT5 MACHINE: Initiating high-priority API-DRIVEN login sequence...")

        path = self.discover_terminal()
        if not path:
            print("MT5 MACHINE: CRITICAL - terminal64.exe missing.")
            return False

        # Use data path if provided in environment
        data_path = os.getenv("MT5_DATA_PATH", "")

        max_attempts = 5
        for i in range(1, max_attempts + 1):
            print(f"\n--- MT5 CONNECTION ATTEMPT {i}/{max_attempts} ---")

            # Step 1: Prove IPC Bridge Readiness
            # We don't relaunch unless initialization fails completely
            print(f"MT5 MACHINE: Initializing IPC bridge to {path}...")

            # Mandatory sequence: path, then explicit login
            init_args = {"path": path}
            if data_path:
                # Note: datapath is handled via Start-Process in GHA, but we pass it here too if supported
                print(f"MT5 MACHINE: Targeting Data Path: {data_path}")

            if self.mt5.initialize(**init_args):
                print(f"MT5 MACHINE: IPC Bridge ONLINE. Version: {self.mt5.version()}")

                # Active Wait for Terminal Readiness (Verify UI/Internal state)
                for wait_i in range(1, 13):
                    t_info = self.mt5.terminal_info()
                    if t_info:
                        print(f"MT5 MACHINE: Terminal Ready. Connected to network: {t_info.connected}")
                        break
                    print(f"MT5 MACHINE: Waiting for Terminal API readiness ({wait_i}/12)...")
                    time.sleep(10)

                # Step 2: Explicit Login
                print(f"MT5 MACHINE: Performing explicit login to {self.server}...")
                if self.mt5.login(login=int(self.login_id), password=self.password, server=self.server):
                    # Step 3: Prove Account Readiness
                    account = self.mt5.account_info()
                    if account and account.login == int(self.login_id):
                        print(f"MT5 MACHINE: SUCCESS | Account: {account.login} | Balance: ${account.balance}")
                        return True
                    else:
                        print(f"MT5 MACHINE: Login succeeded but account verification failed. Error: {self.mt5.last_error()}")
                else:
                    print(f"MT5 MACHINE: Login call failed. Error: {self.mt5.last_error()}")
            else:
                print(f"MT5 MACHINE: IPC Initialization failed. Error: {self.mt5.last_error()}")

            # If we reach here, attempt relaunch for next try
            print("MT5 MACHINE: Attempting process relaunch...")
            self.kill_mt5()
            self.launch_mt5(path)
            time.sleep(30)

        print("\nMT5 MACHINE: MT5 FAILED TO REACH READY STATE.")
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
