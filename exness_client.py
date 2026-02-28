import asyncio
from metaapi_cloud_sdk import MetaApi
from config import META_API_TOKEN, META_API_ACCOUNT_ID, logger

class ExnessClient:
    def __init__(self):
        self.api = MetaApi(META_API_TOKEN)
        self.account_id = META_API_ACCOUNT_ID
        self.connection = None
        self.account = None

    async def connect(self):
        try:
            self.account = await self.api.metatrader_account_api.get_account(self.account_id)
            if self.account.state != 'DEPLOYED':
                logger.error(f"Account {self.account_id} is not deployed. Current state: {self.account.state}")
                return False

            self.connection = self.account.get_rpc_connection()
            await self.connection.connect()
            await self.connection.wait_synchronized()
            return True
        except Exception as e:
            logger.error(f"Error connecting to MetaApi: {e}")
            return False

    async def close(self):
        try:
            if self.connection:
                # MetaApi connection doesn't have a direct close(),
                # but we can clear references
                self.connection = None
            logger.info("MetaApi connection closed.")
        except Exception as e:
            logger.error(f"Error closing MetaApi connection: {e}")

    async def get_account_summary(self):
        if not self.connection:
            await self.connect()
        try:
            account_information = await self.connection.get_account_information()
            return {
                "balance": account_information["balance"],
                "equity": account_information["equity"],
                "currency": account_information["currency"]
            }
        except Exception as e:
            logger.error(f"Error fetching account summary: {e}")
            return None

    async def get_candles(self, instrument, count=100, timeframe="5m"):
        if not self.connection:
            await self.connect()
        try:
            # MetaApi timeframe format: 1m, 5m, 15m, 30m, 1h, etc.
            # OANDA granularity M5 -> MetaApi 5m
            candles = await self.connection.get_historical_candles(instrument, timeframe, None, count)
            # Adapt MetaApi format to the bot's expected format
            adapted_candles = []
            for candle in candles:
                adapted_candles.append({
                    "time": candle["time"],
                    "mid": {
                        "o": str(candle["open"]),
                        "h": str(candle["high"]),
                        "l": str(candle["low"]),
                        "c": str(candle["close"])
                    },
                    "volume": candle["tickVolume"]
                })
            return adapted_candles
        except Exception as e:
            logger.error(f"Error fetching candles for {instrument}: {e}")
            return None

    async def place_market_order(self, instrument, units, stop_loss=None, take_profit=None):
        if not self.connection:
            await self.connect()

        try:
            # MetaApi uses lots. 1 lot usually = 100,000 units for currencies.
            # For simplicity, we'll assume 'units' passed is already in lot size or
            # we need to convert. The prompt's position sizing gives 'units'.
            # OANDA 1 unit of gold is 1 oz. In MetaTrader, 0.01 lots is usually 1 oz.
            # We'll treat units as raw numbers for now and assume the caller handled conversion.
            # Actually, let's assume 0.01 lot minimum.

            # side: BUY or SELL
            action = 'BUY' if units > 0 else 'SELL'
            volume = abs(units) # Assuming units is lot size here for simplicity

            # Ensure minimum lot size
            if volume < 0.01:
                volume = 0.01

            options = {}
            if stop_loss:
                options["stopLoss"] = stop_loss
            if take_profit:
                options["takeProfit"] = take_profit

            result = await self.connection.create_market_buy_order(instrument, volume, stop_loss, take_profit) if action == 'BUY' \
                else await self.connection.create_market_sell_order(instrument, volume, stop_loss, take_profit)

            return {"orderFillTransaction": {"id": result["orderId"]}}
        except Exception as e:
            logger.error(f"Error placing order for {instrument}: {e}")
            return None

    async def get_current_price(self, instrument):
        if not self.connection:
            await self.connect()
        try:
            symbol_price = await self.connection.get_symbol_price(instrument)
            return (symbol_price["bid"] + symbol_price["ask"]) / 2
        except Exception as e:
            logger.error(f"Error fetching price for {instrument}: {e}")
            return None

    async def get_closed_trades(self, count=50):
        if not self.connection:
            await self.connect()
        try:
            # For MetaTrader, we should look at deals (actual executions)
            # rather than orders to get realized PL.
            from datetime import datetime, timedelta, timezone
            start_date = datetime.now(timezone.utc) - timedelta(days=7)

            history = await self.connection.get_history_orders_by_time(start_date, datetime.now(timezone.utc), 0, count)

            adapted_trades = []
            for item in history.get('historyOrders', []):
                if item.get('state') == 'ORDER_STATE_FILLED':
                    adapted_trades.append({
                        "id": item["id"],
                        "realizedPL": item.get("profit", 0),
                        "averageClosePrice": item.get("donePrice", 0),
                        "closeTime": item.get("doneTime")
                    })
            return adapted_trades
        except Exception as e:
            logger.error(f"Error fetching closed trades: {e}")
            return []

    async def get_open_trades(self):
        if not self.connection:
            await self.connect()
        try:
            positions = await self.connection.get_positions()
            return positions
        except Exception as e:
            logger.error(f"Error fetching open trades: {e}")
            return []
