import requests
import json
from config import OANDA_TOKEN, OANDA_ACCOUNT_ID, OANDA_URL, logger

class OandaClient:
    def __init__(self):
        self.headers = {
            "Authorization": f"Bearer {OANDA_TOKEN}",
            "Content-Type": "application/json"
        }
        self.account_id = OANDA_ACCOUNT_ID
        self.base_url = OANDA_URL

    def get_account_summary(self):
        url = f"{self.base_url}/accounts/{self.account_id}/summary"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("account")
        except Exception as e:
            logger.error(f"Error fetching account summary: {e}")
            return None

    def get_candles(self, instrument, count=100, granularity="M5"):
        url = f"{self.base_url}/instruments/{instrument}/candles"
        params = {
            "count": count,
            "granularity": granularity,
            "price": "MBA" # Mid, Bid, Ask
        }
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("candles")
        except Exception as e:
            logger.error(f"Error fetching candles for {instrument}: {e}")
            return None

    def place_market_order(self, instrument, units, stop_loss=None, take_profit=None):
        url = f"{self.base_url}/accounts/{self.account_id}/orders"

        # OANDA units: positive for long, negative for short
        order_data = {
            "order": {
                "units": str(units),
                "instrument": instrument,
                "timeInForce": "FOK",
                "type": "MARKET",
                "positionFill": "DEFAULT"
            }
        }

        if stop_loss:
            order_data["order"]["stopLossOnFill"] = {"price": f"{stop_loss:.5f}"}
        if take_profit:
            order_data["order"]["takeProfitOnFill"] = {"price": f"{take_profit:.5f}"}

        try:
            response = requests.post(url, headers=self.headers, data=json.dumps(order_data))
            response.raise_for_status()
            return response.json()
        except Exception as e:
            logger.error(f"Error placing order for {instrument}: {e}")
            if hasattr(e, 'response') and e.response is not None:
                logger.error(f"Response: {e.response.text}")
            return None

    def get_current_price(self, instrument):
        url = f"{self.base_url}/accounts/{self.account_id}/pricing"
        params = {"instruments": instrument}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            prices = response.json().get("prices")
            if prices:
                # Use mid price: (bid + ask) / 2
                bid = float(prices[0]["bids"][0]["price"])
                ask = float(prices[0]["asks"][0]["price"])
                return (bid + ask) / 2
            return None
        except Exception as e:
            logger.error(f"Error fetching price for {instrument}: {e}")
            return None

    def get_closed_trades(self, count=50):
        url = f"{self.base_url}/accounts/{self.account_id}/trades"
        params = {"state": "CLOSED", "count": count}
        try:
            response = requests.get(url, headers=self.headers, params=params)
            response.raise_for_status()
            return response.json().get("trades", [])
        except Exception as e:
            logger.error(f"Error fetching closed trades: {e}")
            return []

    def get_open_trades(self):
        url = f"{self.base_url}/accounts/{self.account_id}/openTrades"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            return response.json().get("trades", [])
        except Exception as e:
            logger.error(f"Error fetching open trades: {e}")
            return []
