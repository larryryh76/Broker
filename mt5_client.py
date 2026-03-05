import os
import time
import subprocess
import shutil

try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

try:
    import winreg
except ImportError:
    winreg = None

from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, logger

class MT5Client:
    def __init__(self):
        self.login = MT5_LOGIN
        self.password = MT5_PASSWORD
        self.server = MT5_SERVER
        self._connected = False
        self.mt5 = mt5

    def _set_registry_bypass(self):
        """Inject EULA acceptance into the Windows Registry to skip GUI popups."""
        if winreg is None:
            return
        try:
            # Registry path for MT5
            key_path = r"Software\MetaQuotes Software\MetaTrader 5"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "AcceptedLicense", 0, winreg.REG_DWORD, 1)
                logger.info("Registry Bypass: AcceptedLicense set to 1.")
        except Exception as e:
            logger.error(f"Registry bypass failed: {e}")

    def _create_dummy_dll(self, terminal_dir):
        """Create a dummy WebView2Loader.dll to prevent terminal hangs."""
        dll_path = os.path.join(terminal_dir, "WebView2Loader.dll")
        if not os.path.exists(dll_path):
            try:
                with open(dll_path, "wb") as f:
                    f.write(b"")
                logger.info(f"Created dummy DLL at: {dll_path}")
            except Exception as e:
                logger.error(f"Failed to create dummy DLL: {e}")

    def _inject_server_data(self, config_dir):
        """EMERGENCY OVERRIDE: Binary Injection of Server Data to bypass sync hangs."""
        server_path = os.path.join(config_dir, "servers.dat")
        try:
            # Create/overwrite with non-zero byte content
            with open(server_path, "wb") as f:
                f.write(b"\x00")

            # Ensure not read-only
            if hasattr(os, "chmod"):
                os.chmod(server_path, 0o666)

            size = os.path.getsize(server_path)
            logger.info(f"Binary Injection: servers.dat created ({size} bytes).")
        except Exception as e:
            logger.error(f"Server data injection failed: {e}")

    def connect(self):
        if self._connected:
            return True

        workspace = os.getcwd()

        def find_terminal():
            search_paths = [
                os.path.join(workspace, "mt5_terminal", "terminal64.exe"),
                "C:\\Program Files\\FBS MetaTrader 5\\terminal64.exe",
                "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
            ]
            for path in search_paths:
                if os.path.exists(path):
                    return path
            return None

        terminal_path = find_terminal()
        if not terminal_path:
            logger.error("Could not find terminal64.exe")
            return False

        terminal_path = os.path.abspath(terminal_path)
        terminal_dir = os.path.dirname(terminal_path)

        # Surgical Fix 1: Physically delete bases and logs BEFORE Cycle 1 to skip sync
        for folder in ["bases", "logs"]:
            folder_path = os.path.join(terminal_dir, folder)
            if os.path.exists(folder_path):
                logger.info(f"Removing corrupted cache: {folder_path}")
                try:
                    shutil.rmtree(folder_path, ignore_errors=True)
                except Exception as e:
                    logger.error(f"Failed to clear {folder}: {e}")

        # Surgical Fix 2: WebView Bypass & Registry Injection
        self._set_registry_bypass()
        self._create_dummy_dll(terminal_dir)

        # 1. Shell-Level Initialization & Injection
        config_dir = os.path.join(terminal_dir, "config")
        if not os.path.exists(config_dir):
            os.makedirs(config_dir)

        # Binary Injection of Server Data
        self._inject_server_data(config_dir)

        # Surgical Fix: Configuration Injection
        common_path = os.path.join(config_dir, "common.ini")
        common_content = (
            f"[Common]\n"
            f"Login={self.login}\n"
            f"ProxyEnable=0\n"
            f"CertifyEnable=0\n"
            f"NewsEnable=0\n"
            f"ChartsEnable=0\n"
            f"SignalsEnable=0\n"
            f"MarketEnable=0\n"
        )
        with open(common_path, "w") as f:
            f.write(common_content)

        ini_content = (
            f"[Common]\n"
            f"Login={self.login}\n"
            f"Password={self.password}\n"
            f"Server={self.server}\n"
            f"ExpertsEnable=1\n"
            f"AllowLiveTrading=1\n"
            f"AllowDllImport=1\n"
            f"Enabled=1\n"
            f"[Experts]\n"
            f"AllowLiveTrading=1\n"
            f"Enabled=1\n"
            f"[Charts]\n"
            f"Experts=1\n"
        )
        for ini_name in ["startup.ini", "accounts.ini"]:
            path = os.path.join(config_dir, ini_name)
            with open(path, "w") as f:
                f.write(ini_content)

        config_path = os.path.join(config_dir, "startup.ini")

        # Diagnostic Check: Verify directory population
        try:
            logger.info(f"Diagnostic - Terminal Root Contents: {os.listdir(terminal_dir)}")
        except Exception as e:
            logger.error(f"Diagnostic listdir failed: {e}")

        # Launch terminal ONCE for 'Stamina' Handshake
        logger.info("Launching terminal for 'Stamina' Handshake...")
        subprocess.Popen([
            terminal_path, "/portable",
            f"/config:{config_path}",
            f"/login:{self.login}",
            "/notest", "/nosound",
            "/skipupdate", "/novisual"
        ])

        # 2. 'Stamina' Handshake Window (No Killing)
        # Call initialize() every 10 seconds for 2 minutes
        logger.info("Starting 'Stamina' Handshake loop (120s max)...")
        for i in range(12):
            logger.info(f"Handshake attempt {i+1}/12...")
            try:
                init_success = False
                try:
                    init_success = mt5.initialize(
                        path=terminal_path,
                        common_metadata_path=workspace,
                        timeout=20000,
                        portable=True
                    )
                except TypeError:
                    init_success = mt5.initialize(path=terminal_path, timeout=20000)

                if init_success:
                    # 3. Account Force-Login
                    logger.info("Initialize successful. Triggering Force-Login...")
                    if mt5.login(login=self.login, password=self.password, server=self.server):
                        # 4. Data Warmup
                        logger.info("Force-Login SUCCESS. Performing Data Warmup...")
                        rates = mt5.copy_rates_from_pos('EURUSD', mt5.TIMEFRAME_M1, 0, 10)
                        if rates is not None and len(rates) > 0:
                            acc_info = mt5.account_info()
                            logger.info(f"STAMINA SUCCESS. Active Intelligence Balance: ${acc_info.balance:.2f}")
                            self._connected = True
                            break
                        else:
                            logger.warning("Warmup returned NO DATA. Retrying...")
                    else:
                        logger.error(f"Force-Login FAILED: {mt5.last_error()}")

            except Exception as e:
                logger.error(f"Error in handshake {i+1}: {e}")

            time.sleep(10)

        if self._connected:
            # Proceed with FBS-specific symbol mapping (once connected)
            try:
                # FBS Account Type Detection & Symbol Mapping
                acc_info = mt5.account_info()
                if acc_info:
                    if "cent" in acc_info.server.lower() or "cent" in acc_info.company.lower():
                        logger.info("FBS CENT Account detected. Adjusting specs.")

                from config import INSTRUMENTS
                actual_instruments = []
                for sym in INSTRUMENTS:
                    found_sym = None
                    candidates = [sym, sym + "-mt5", sym + "m"]
                    for candidate in candidates:
                        if mt5.symbol_select(candidate, True):
                            mt5.copy_rates_from_pos(candidate, mt5.TIMEFRAME_M5, 0, 100)
                            found_sym = candidate
                            break
                    if found_sym:
                        actual_instruments.append(found_sym)
                        logger.info(f"FBS Symbol mapped: {sym} -> {found_sym}")
                    else:
                        logger.warning(f"FBS Symbol mapping failed for {sym}. Skipping.")

                import config
                config.INSTRUMENTS = actual_instruments
                return True
            except Exception as e:
                logger.error(f"Error during symbol mapping: {e}")
                return True # Still connected

        return False

    def close(self):
        mt5.shutdown()
        logger.info("MT5 connection closed.")

    def get_account_summary(self):
        if not self.connect():
            return None
        account_info = mt5.account_info()
        if account_info is None:
            logger.error(f"Failed to get account info, error: {mt5.last_error()}")
            return None
        return {
            "balance": account_info.balance,
            "equity": account_info.equity,
            "currency": account_info.currency
        }

    def get_candles(self, instrument, count=100, timeframe=None):
        if timeframe is None:
            timeframe = mt5.TIMEFRAME_M5 if mt5 else 16389 # 16389 is M5 in MT5
        if not self.connect():
            return None

        rates = mt5.copy_rates_from_pos(instrument, timeframe, 0, count)
        if rates is None:
            logger.error(f"Failed to copy rates for {instrument}, error: {mt5.last_error()}")
            return None

        adapted_candles = []
        for rate in rates:
            adapted_candles.append({
                "time": int(rate['time']), # MT5 returns unix timestamp
                "mid": {
                    "o": str(rate['open']),
                    "h": str(rate['high']),
                    "l": str(rate['low']),
                    "c": str(rate['close'])
                },
                "volume": int(rate['tick_volume'])
            })
        return adapted_candles

    def symbol_info(self, instrument):
        if not self.connect():
            return None
        return mt5.symbol_info(instrument)

    def symbol_info_tick(self, instrument):
        if not self.connect():
            return None
        return mt5.symbol_info_tick(instrument)

    def check_trade_allowed(self):
        if not self.connect():
            return False
        info = mt5.terminal_info()
        if info is None:
            return False
        if not info.trade_allowed:
            logger.critical("CRITICAL: Trading Blocked (trade_allowed is False)")
            return False
        return True

    def place_market_order(self, instrument, volume, stop_loss=None, take_profit=None):
        if not self.connect():
            return None

        # Check if trading is allowed before placing order
        self.check_trade_allowed()

        # Determine side
        tick = mt5.symbol_info_tick(instrument)
        if not tick:
            logger.error(f"Could not get tick info for {instrument}")
            return None

        order_type = mt5.ORDER_TYPE_BUY if volume > 0 else mt5.ORDER_TYPE_SELL
        price = tick.ask if volume > 0 else tick.bid

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": instrument,
            "volume": abs(float(volume)),
            "type": order_type,
            "price": price,
            "sl": float(stop_loss) if stop_loss else 0.0,
            "tp": float(take_profit) if take_profit else 0.0,
            "deviation": 20,
            "magic": 123456,
            "comment": "MoneyMachine Bot",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)

        # Fallback to FOK if IOC fails with AutoTrading error (10017) or filling error
        if result and result.retcode in [mt5.TRADE_RETCODE_REJECT, 10017, 10030]:
            logger.warning(f"IOC filling failed (Retcode {result.retcode}). Retrying with FOK filling...")
            request["type_filling"] = mt5.ORDER_FILLING_FOK
            result = mt5.order_send(request)

        if result is None:
            error_code = mt5.last_error()
            numeric_code = error_code[0] if isinstance(error_code, (list, tuple)) else error_code
            logger.error(f"Order send failed completely. MT5 Error Code: {numeric_code}")
            return None
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order send failed. MT5 Retcode: {result.retcode} (Error {result.retcode}), comment: {result.comment}")
            return None

        return {"orderFillTransaction": {"id": str(result.order)}}

    def get_current_price(self, instrument):
        if not self.connect():
            return None
        tick = mt5.symbol_info_tick(instrument)
        if tick is None:
            return None
        return (tick.bid + tick.ask) / 2

    def calculate_margin(self, instrument, order_type, volume, price):
        if not self.connect():
            return None
        margin = mt5.order_calc_margin(order_type, instrument, volume, price)
        if margin is None:
            logger.error(f"Failed to calculate margin for {instrument}: {mt5.last_error()}")
        return margin

    def get_closed_trades(self, count=50):
        if not self.connect():
            return []

        from datetime import datetime, timedelta
        # Fetch history for the last 7 days
        from_date = datetime.now() - timedelta(days=7)
        to_date = datetime.now()

        # history_deals_get returns deals (actual executions)
        # Filtering by MAGIC number (123456) to ignore historical manual trades or "Revenge" data
        deals = mt5.history_deals_get(from_date, to_date)
        if deals is None:
            return []

        adapted_trades = []
        for deal in deals:
            # ONLY consider deals executed by this bot's magic number
            if deal.magic != 123456:
                continue

            # We want entry/exit deals that resulted in a closed position
            if deal.entry == mt5.DEAL_ENTRY_OUT: # Exit deal
                adapted_trades.append({
                    "id": str(deal.order), # Map to order ID we stored
                    "realizedPL": deal.profit,
                    "averageClosePrice": deal.price,
                    "closeTime": deal.time
                })
        return adapted_trades[-count:]

    def get_open_trades(self):
        if not self.connect():
            return []
        # Filter by Magic Number to ignore manual/historical trades (like BTC)
        positions = mt5.positions_get(magic=123456)
        if positions is None:
            return []

        adapted_positions = []
        for p in positions:
            # Double check magic and filter by active instruments if needed
            from config import INSTRUMENTS
            monitored = False
            for inst in INSTRUMENTS:
                if inst in p.symbol:
                    monitored = True
                    break

            if monitored:
                adapted_positions.append({
                    "symbol": p.symbol,
                    "ticket": p.ticket,
                    "profit": p.profit,
                    "price_open": p.price_open,
                    "type": p.type,
                    "sl": p.sl,
                    "tp": p.tp
                })
        return adapted_positions

    def positions_get(self, ticket=None):
        if not self.connect():
            return None
        if ticket:
            return mt5.positions_get(ticket=ticket)
        return mt5.positions_get()

    def modify_position_sl(self, ticket, sl, tp):
        if not self.connect():
            return False

        pos = mt5.positions_get(ticket=ticket)
        if not pos:
            return False

        request = {
            "action": mt5.TRADE_ACTION_SLTP,
            "position": ticket,
            "sl": float(sl),
            "tp": float(tp)
        }

        result = mt5.order_send(request)
        if result is None:
            error_code = mt5.last_error()
            numeric_code = error_code[0] if isinstance(error_code, (list, tuple)) else error_code
            logger.error(f"Modify SL failed completely for {ticket}. MT5 Error Code: {numeric_code}")
            return False
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Modify SL failed for {ticket}: Retcode {result.retcode}, comment: {result.comment}")
            return False
        return True

    def close_position(self, ticket):
        if not self.connect():
            return False

        pos = mt5.positions_get(ticket=ticket)
        if not pos or len(pos) == 0:
            return False

        pos = pos[0]
        symbol = pos.symbol
        volume = pos.volume
        order_type = mt5.ORDER_TYPE_SELL if pos.type == mt5.POSITION_TYPE_BUY else mt5.ORDER_TYPE_BUY
        price = mt5.symbol_info_tick(symbol).bid if order_type == mt5.ORDER_TYPE_SELL else mt5.symbol_info_tick(symbol).ask

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": symbol,
            "volume": float(volume),
            "type": order_type,
            "position": ticket,
            "price": price,
            "deviation": 20,
            "magic": 123456,
            "comment": "MoneyMachine Close",
            "type_time": mt5.ORDER_TIME_GTC,
            "type_filling": mt5.ORDER_FILLING_IOC,
        }

        result = mt5.order_send(request)
        if result and result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Close failed for {ticket}: Retcode {result.retcode}, comment: {result.comment}")
            return False

        return True
