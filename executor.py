import time
import random
from config import logger, DAILY_DRAWDOWN_LIMIT

class Executor:
    def __init__(self, mt5_client, db_client, strategy):
        self.mt5 = mt5_client
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

    def run_cycle(self, instruments, target=50.0):
        logger.info("Starting 5-minute execution cycle...")

        # 0. Recursive Learning Adjustment
        latest_state = self.db.get_latest_learning_state()
        if latest_state:
            self.strategy.adjust_parameters(latest_state)

        # 1. Initialization
        account = self.mt5.get_account_summary()
        if not account:
            return

        balance = float(account["balance"])
        logger.info(f"Current balance: ${balance}")

        if self.check_circuit_breaker(balance):
            logger.info("Trading halted due to circuit breaker.")
            return

        # 1.5 Check for open positions to avoid duplicates
        open_positions = self.mt5.get_open_trades()
        open_instruments = [p["symbol"] for p in open_positions]

        # 2. Market Data and Signal Generation
        signals = []
        for instrument in instruments:
            if instrument in open_instruments:
                logger.info(f"Already have an open position for {instrument}. Skipping.")
                continue

            candles = self.mt5.get_candles(instrument)
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
            self.execute_signal(signal, balance, target=target)

    def manage_open_positions(self):
        """
        Zero-Risk Trigger & Aggressive Trailing Stop
        """
        positions = self.mt5.get_open_trades()
        for p in positions:
            symbol = p["symbol"]
            ticket = p["ticket"]

            # Fetch current position details from MT5 directly for precise info
            pos_info = self.mt5.positions_get(ticket=ticket)
            if not pos_info:
                continue

            pos = pos_info[0]
            symbol_info = self.mt5.symbol_info(symbol)
            tick = self.mt5.symbol_info_tick(symbol)
            if not symbol_info or not tick:
                continue

            price_open = pos.price_open
            price_current = tick.bid if pos.type == 0 else tick.ask # BUY: Bid, SELL: Ask
            sl_current = pos.sl
            tp_current = pos.tp

            # Points of profit
            profit_points = abs(price_current - price_open) / symbol_info.point

            # 1. Zero-Risk Trigger: Move SL to break-even after 50 points profit
            if profit_points >= 50 and sl_current == 0:
                logger.info(f"Zero-Risk Trigger: Moving SL to break-even for {symbol} ({ticket})")
                self.mt5.modify_position_sl(ticket, price_open, tp_current)

            # 2. Aggressive Trailing: 10-point trail once safe (sl != 0)
            elif sl_current != 0:
                new_sl = 0
                if pos.type == 0: # BUY
                    if price_current - sl_current > 10 * symbol_info.point:
                        new_sl = price_current - 10 * symbol_info.point
                else: # SELL
                    if sl_current - price_current > 10 * symbol_info.point:
                        new_sl = price_current + 10 * symbol_info.point

                if new_sl != 0:
                    logger.info(f"Aggressive Trailing: Moving SL to {new_sl} for {symbol} ({ticket})")
                    self.mt5.modify_position_sl(ticket, new_sl, tp_current)

    def execute_signal(self, signal, balance, target=50.0):
        instrument = signal["instrument"]
        side = signal["side"]
        price = signal["price"]
        confidence = signal["confidence"]

        # Max Spread Check: 20 points
        symbol_info = self.mt5.symbol_info(instrument)
        tick = self.mt5.symbol_info_tick(instrument)
        if symbol_info and tick:
            spread_points = (tick.ask - tick.bid) / symbol_info.point
            if spread_points > 20:
                logger.warning(f"Spread too high for {instrument}: {spread_points} points. Skipping.")
                return

        # Check if balance is extremely low for the instrument
        if balance < 10 and ("BTC" in instrument or "XAU" in instrument):
            logger.warning(f"Balance too low to trade {instrument}. Skipping.")
            return

        # 4. Risk Assessment & Levels
        stop_loss, take_profit = self.strategy.calculate_levels(side, price)

        # 5. Position Sizing
        units = self.strategy.calculate_position_size(balance, target=target)

        # Side: positive for BUY, negative for SELL
        order_volume = units if side == "BUY" else -units

        # 6. Aggressive Signal: No delays

        logger.info(f"Executing {side} order for {instrument} with {units} lots...")
        order_result = self.mt5.place_market_order(instrument, order_volume, stop_loss, take_profit)

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
