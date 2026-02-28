import asyncio
import time
import random
from config import logger, DAILY_DRAWDOWN_LIMIT

class Executor:
    def __init__(self, exness_client, db_client, strategy):
        self.exness = exness_client
        self.db = db_client
        self.strategy = strategy

    def check_circuit_breaker(self, balance):
        latest_state = self.db.get_latest_learning_state()
        if not latest_state:
            return False

        from datetime import datetime, timezone
        state_time = latest_state["timestamp"]
        if state_time.tzinfo is None:
            state_time = state_time.replace(tzinfo=timezone.utc)

        # Only apply circuit breaker if the state is from today
        if state_time.date() == datetime.now(timezone.utc).date():
            initial_daily_balance = latest_state.get("initial_daily_balance", balance)
            drawdown = (initial_daily_balance - balance) / initial_daily_balance

            if drawdown >= DAILY_DRAWDOWN_LIMIT:
                logger.warning(f"CIRCUIT BREAKER ACTIVATED: Drawdown is {drawdown*100:.2f}% (Limit: {DAILY_DRAWDOWN_LIMIT*100}%)")
                return True
        return False

    async def run_cycle(self, instruments):
        logger.info("Starting 5-minute execution cycle...")

        # 0. Recursive Learning Adjustment
        latest_state = self.db.get_latest_learning_state()
        if latest_state:
            self.strategy.adjust_parameters(latest_state)

        # 1. Initialization
        account = await self.exness.get_account_summary()
        if not account:
            return

        balance = float(account["balance"])
        logger.info(f"Current balance: ${balance}")

        if self.check_circuit_breaker(balance):
            logger.info("Trading halted due to circuit breaker.")
            return

        # 1.5 Check for open positions to avoid duplicates
        open_positions = await self.exness.get_open_trades()
        open_instruments = [p["symbol"] for p in open_positions]

        # 2. Market Data and Signal Generation
        signals = []
        for instrument in instruments:
            if instrument in open_instruments:
                logger.info(f"Already have an open position for {instrument}. Skipping.")
                continue

            candles = await self.exness.get_candles(instrument)
            if not candles:
                continue

            df = self.strategy.prepare_data(candles)
            df = self.strategy.calculate_indicators(df)
            signal = self.strategy.generate_signal(df)

            if signal and signal["side"] != "SKIP":
                signal["instrument"] = instrument
                signals.append(signal)
                logger.info(f"Signal generated for {instrument}: {signal['side']} at {signal['price']} with {signal['confidence']*100}% confidence")
            else:
                logger.info(f"No signal for {instrument}")

        # 3. Execution (to be expanded with stealth delay and risk assessment)
        for signal in signals:
            await self.execute_signal(signal, balance)

    async def execute_signal(self, signal, balance):
        instrument = signal["instrument"]
        side = signal["side"]
        price = signal["price"]
        confidence = signal["confidence"]

        # Check if balance is extremely low for the instrument
        # BTC_USD usually requires much more margin than $5 even for 1 unit
        # OANDA allows fractional units for some instruments but not all.
        # For XAU_USD, 1 unit is 1 ounce. Current price ~$2000+.
        # Even with 1:100 leverage, $5 isn't enough for 1 unit of gold ($20 margin).
        if balance < 10 and ("BTC" in instrument or "XAU" in instrument):
            logger.warning(f"Balance too low to trade {instrument}. Skipping.")
            return

        # 4. Risk Assessment & Levels
        stop_loss, take_profit = self.strategy.calculate_levels(side, price)

        # 5. Position Sizing
        units = self.strategy.calculate_position_size(balance, price, stop_loss, confidence)

        # OANDA units: positive for BUY, negative for SELL
        oanda_units = units if side == "BUY" else -units

        # 6. Stealth Execution: Randomized delay
        delay = random.randint(30, 290)
        logger.info(f"Stealth execution for {instrument}: Waiting {delay} seconds before entry...")
        await asyncio.sleep(delay)

        # Re-fetch current price just before execution for better accuracy
        current_price = await self.exness.get_current_price(instrument)
        if current_price:
            # Recalculate levels based on current price if it moved significantly?
            # Prompt says "Submit market orders at the randomized execution time"
            # We'll use the original SL/TP distances but apply to current price
            price = current_price
            stop_loss, take_profit = self.strategy.calculate_levels(side, price)

        logger.info(f"Executing {side} order for {instrument} with {units} lots...")
        order_result = await self.exness.place_market_order(instrument, oanda_units, stop_loss, take_profit)

        if order_result:
            logger.info(f"Order executed successfully: {order_result.get('orderFillTransaction', {}).get('id')}")
            # 7. Trade Logging
            trade_data = {
                "instrument": instrument,
                "side": side,
                "entry_price": price,
                "stop_loss": stop_loss,
                "take_profit": take_profit,
                "units": units,
                "confidence": confidence,
                "order_id": order_result.get('orderFillTransaction', {}).get('id'),
                "entry_time": time.time()
            }
            self.db.log_trade(trade_data)
        else:
            logger.error(f"Failed to execute order for {instrument}")
