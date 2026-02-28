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

    def connect(self):
        if not mt5.initialize(login=self.login, password=self.password, server=self.server):
            logger.error(f"MT5 initialize failed, error code: {mt5.last_error()}")
            return False
        return True

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

    def place_market_order(self, instrument, volume, stop_loss=None, take_profit=None):
        if not self.connect():
            return None

        # Determine side
        order_type = mt5.ORDER_TYPE_BUY if volume > 0 else mt5.ORDER_TYPE_SELL
        price = mt5.symbol_info_tick(instrument).ask if volume > 0 else mt5.symbol_info_tick(instrument).bid

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
        if result.retcode != mt5.TRADE_RETCODE_DONE:
            logger.error(f"Order send failed, retcode: {result.retcode}, error: {mt5.last_error()}")
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
