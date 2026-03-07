import os
import time
import subprocess
import shutil

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
        self.mt5 = mt5

    def connect(self):
        if self._connected:
            return True

        workspace = os.getcwd()

        def find_terminal():
            # Prioritize repository path for GitHub Actions
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

        # 1. Terminate existing terminal instances to ensure clean start
        logger.info("Terminating existing terminal instances...")
        try:
            os.system('taskkill /f /im terminal64.exe /t 2>NUL')
        except:
            pass
        time.sleep(2)

        # 2. Launch terminal in portable mode
        logger.info(f"Launching MT5 Terminal: {terminal_path}")
        try:
            subprocess.Popen([terminal_path, "/portable"])
        except Exception as e:
            logger.error(f"Failed to launch terminal process: {e}")
            return False

        # 3. Robust Initialization Window (60s)
        logger.info("Waiting 60 seconds for terminal GUI and IPC to stabilize...")
        time.sleep(60)

        # 4. Retry strategy for mt5.initialize()
        max_retries = 5
        retry_delay = 10

        for attempt in range(1, max_retries + 1):
            logger.info(f"Establishing IPC bridge (Attempt {attempt}/{max_retries})...")
            try:
                init_success = False
                # Use credentials for explicit login during initialization
                try:
                    init_success = mt5.initialize(
                        path=terminal_path,
                        login=self.login,
                        password=self.password,
                        server=self.server,
                        portable=True,
                        timeout=60000
                    )
                except TypeError:
                    # Compatibility with older versions of library
                    init_success = mt5.initialize(
                        terminal_path,
                        login=self.login,
                        password=self.password,
                        server=self.server,
                        timeout=60000
                    )

                if init_success:
                    logger.info("IPC bridge established and MT5 logged in.")
                    self._connected = True
                    break
                else:
                    error_msg = str(mt5.last_error())
                    logger.warning(f"Initialization attempt failed: {error_msg}")
                    if attempt < max_retries:
                        time.sleep(retry_delay)
            except Exception as e:
                logger.error(f"Critical error during mt5.initialize(): {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)

        if self._connected:
            # Perform symbol discovery and mapping
            try:
                from config import INSTRUMENTS
                actual_instruments = []
                for sym in INSTRUMENTS:
                    found_sym = None
                    # FBS specific symbol mapping (common suffixes)
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
                        logger.warning(f"FBS Symbol mapping failed for {sym}")

                import config
                config.INSTRUMENTS = actual_instruments
                return True
            except Exception as e:
                logger.error(f"Error during post-initialization symbol mapping: {e}")
                return True # Connection itself is fine

        return False

    def close(self):
        if self.mt5:
            self.mt5.shutdown()
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
                "time": int(rate['time']),
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

        self.check_trade_allowed()

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

        if result and result.retcode in [mt5.TRADE_RETCODE_REJECT, 10017, 10030]:
            logger.warning(f"IOC filling failed (Retcode {result.retcode}). Retrying with FOK filling...")
            request["type_filling"] = mt5.ORDER_FILLING_FOK
            result = mt5.order_send(request)

        if result is None:
            error_code = mt5.last_error()
            logger.error(f"Order send failed completely. MT5 Error: {error_code}")
            return None
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order send failed. Retcode: {result.retcode}, comment: {result.comment}")
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
        from_date = datetime.now() - timedelta(days=7)
        to_date = datetime.now()

        deals = mt5.history_deals_get(from_date, to_date)
        if deals is None:
            return []

        adapted_trades = []
        for deal in deals:
            if deal.magic != 123456:
                continue

            if deal.entry == mt5.DEAL_ENTRY_OUT:
                adapted_trades.append({
                    "id": str(deal.order),
                    "realizedPL": deal.profit,
                    "averageClosePrice": deal.price,
                    "closeTime": deal.time
                })
        return adapted_trades[-count:]

    def get_open_trades(self):
        if not self.connect():
            return []
        positions = mt5.positions_get(magic=123456)
        if positions is None:
            return []

        adapted_positions = []
        for p in positions:
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
        if result is None or result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Modify SL failed for {ticket}.")
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
            logger.error(f"Close failed for {ticket}")
            return False

        return True
