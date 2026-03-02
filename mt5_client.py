try:
    import MetaTrader5 as mt5
except ImportError:
    mt5 = None

from config import MT5_LOGIN, MT5_PASSWORD, MT5_SERVER, logger

class MT5Client:
    def __init__(self):
        self.login = MT5_LOGIN
        self.password = MT5_PASSWORD
        self.server = MT5_SERVER
        self._connected = False

    def connect(self):
        if self._connected:
            return True

        import time
        import os
        import subprocess

        def find_terminal():
            # 1. Fallback to workspace path
            workspace = os.environ.get('GITHUB_WORKSPACE', os.getcwd())
            search_paths = [
                os.path.join(workspace, "mt5_terminal", "terminal64.exe"),
                "C:\\Program Files\\Exness MetaTrader 5\\terminal64.exe",
                "C:\\Program Files\\MetaTrader 5\\terminal64.exe"
            ]
            for path in search_paths:
                if os.path.exists(path):
                    return path
            return None

        terminal_path = find_terminal()
        if terminal_path:
            terminal_path = os.path.abspath(terminal_path)

        # 1. Manual Start via subprocess with config file
        try:
            if terminal_path:
                # Absolute Path Config Fix: Ensure the startup.ini is created relative to terminal64.exe
                terminal_dir = os.path.dirname(os.path.abspath(terminal_path))
                config_dir = os.path.join(terminal_dir, "config")
                if not os.path.exists(config_dir):
                    os.makedirs(config_dir)
                config_path = os.path.join(config_dir, "startup.ini")

                # Dynamic .ini generation for Algo Trading
                ini_content = f"[Common]\nLogin={self.login}\nPassword={self.password}\nServer={self.server}\nExpertsEnable=1\nAllowLiveTrading=1\nAllowDllImport=1\n[Charts]\nExperts=1\n"
                with open(config_path, "w") as f:
                    f.write(ini_content)

                logger.info(f"Generated forced config and launching terminal: {config_path}")

                # Launch with the config file to bypass all GUI prompts
                subprocess.Popen([terminal_path, "/portable", f"/config:{config_path}"])

                # Wait for background process to bridge the IPC pipe
                time.sleep(60)

            # 2. Direct Initialization (Bypassing Handshake)
            if mt5.initialize(path=terminal_path, timeout=60000, portable=True):
                # Ordered Bypass: Proceed directly to trading logic
                logger.info("MT5 initialized. Bypassing all handshake checks and proceeding to trade analysis...")

                # Allow terminal a brief moment to sync internal state (minimal)
                time.sleep(2)
                logger.info(f"Terminal Info: {mt5.terminal_info()}")

                # Force symbol selection into Market Watch with strict 'm' suffix
                from config import INSTRUMENTS
                actual_instruments = []
                for sym in INSTRUMENTS:
                    # Exness Standard requires 'm' suffix
                    found_sym = None
                    candidate = sym + "m" if not sym.endswith("m") else sym
                    if mt5.symbol_select(candidate, True):
                        # Sync history for the symbol
                        mt5.copy_rates_from_pos(candidate, mt5.TIMEFRAME_M5, 0, 100)
                        found_sym = candidate

                    if found_sym:
                        actual_instruments.append(found_sym)
                        logger.info(f"Symbol {found_sym} selected and synced successfully.")
                        # Log symbol info for debugging
                        logger.info(f"{found_sym} Info: {mt5.symbol_info(found_sym)}")
                    else:
                        logger.warning(f"Failed to select {sym} or {sym}m in Market Watch.")

                # Update the global INSTRUMENTS list with the found symbols
                import config
                config.INSTRUMENTS = actual_instruments

                # Check if already logged in from command line
                account_info = mt5.account_info()
                if account_info and account_info.login == self.login:
                    logger.info("MT5 already logged in via command line.")
                    self._connected = True
                    return True

                # 3. Fallback manual login
                if mt5.login(login=self.login, password=self.password, server=self.server):
                    logger.info("MT5 logged in successfully.")
                    self._connected = True
                    return True
                else:
                    logger.error(f"MT5 login failed: {mt5.last_error()}")
            else:
                logger.error(f"MT5 initialize failed: {mt5.last_error()}")
        except Exception as e:
            logger.error(f"Manual start failed: {e}")

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

        # MetaTrader 5 symbols can sometimes have suffixes on Exness
        # We'll try the name directly
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

    def place_market_order(self, instrument, volume, stop_loss=None, take_profit=None):
        if not self.connect():
            return None

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

    def get_closed_trades(self, count=50):
        if not self.connect():
            return []

        from datetime import datetime, timedelta
        # Fetch history for the last 7 days
        from_date = datetime.now() - timedelta(days=7)
        to_date = datetime.now()

        # history_deals_get returns deals (actual executions)
        deals = mt5.history_deals_get(from_date, to_date)
        if deals is None:
            return []

        adapted_trades = []
        for deal in deals:
            # We want entry/exit deals that resulted in a closed position
            # Simplified: just return all deals with profit
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
        positions = mt5.positions_get()
        if positions is None:
            return []

        adapted_positions = []
        for p in positions:
            adapted_positions.append({
                "symbol": p.symbol,
                "ticket": p.ticket
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
