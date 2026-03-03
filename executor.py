import sys
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

    def run_cycle(self, instruments, target=50.0, virtual_balance=5.0):
        logger.info("Scanning for opportunities...")

        # Verification: Check trade permissions
        if not self.mt5.connect():
             logger.error("MT5 connection failed.")
             return

        # Ordered Bypass: Proceeding directly with trade logic as ordered

        # 0. Recursive Learning Adjustment
        latest_state = self.db.get_latest_learning_state()
        if latest_state:
            self.strategy.adjust_parameters(latest_state)

        # 1. Initialization
        account = self.mt5.get_account_summary()
        if not account:
            return

        balance = float(account["balance"])

        if self.check_circuit_breaker(balance):
            logger.info("Trading halted due to circuit breaker.")
            return

        # 1.5 Check for open positions to avoid duplicates
        open_positions = self.mt5.get_open_trades()
        open_instruments = [p["symbol"] for p in open_positions]

        # 2. Market Data and Signal Generation
        # Multi-Asset Rotation: If Gold spread is too high, it will be skipped
        signals = []
        for instrument in instruments:
            if instrument in open_instruments:
                continue

            # Spread Check (Pre-Scan for efficiency)
            symbol_info = self.mt5.symbol_info(instrument)
            tick = self.mt5.symbol_info_tick(instrument)
            if not symbol_info or not tick:
                continue

            spread_points = (tick.ask - tick.bid) / symbol_info.point
            if spread_points > 20:
                # logger.info(f"Skipping {instrument} due to high spread: {spread_points}")
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
                logger.info(f"ALGO SIGNAL: {instrument} {signal['side']} @ {signal['price']} (Spread: {spread_points})")

        # 3. Aggressive Execution: Up to 3 concurrent trades on different symbols
        error_detected = False
        active_slots = len(open_instruments)

        for signal in signals:
            if active_slots >= 3:
                break

            if self.execute_signal(signal, virtual_balance, target=target):
                error_detected = True
            else:
                active_slots += 1

        return error_detected

    def manage_open_positions(self):
        """
        Zero-Risk Trigger & Aggressive Trailing Stop
        """
        # Rate-limiting for AutoTrading errors
        if hasattr(self, '_last_sl_error_time'):
            if time.time() - self._last_sl_error_time < 60:
                return

        positions = self.mt5.get_open_trades()
        for p in positions:
            symbol = p["symbol"]
            ticket = p["ticket"]

            # Fetch current position details from MT5 directly for precise info
            pos_info = self.mt5.positions_get(ticket=ticket)
            if not pos_info or len(pos_info) == 0:
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

            # Current distance from open in points
            dist_from_open = (price_current - price_open) / symbol_info.point if pos.type == 0 else (price_open - price_current) / symbol_info.point

            # 1. No-Loss Protocol: Move SL to break-even at +50 points (5 pips)
            if dist_from_open >= 50 and sl_current == 0:
                logger.info(f"No-Loss LOCK: Moving SL to BREAK-EVEN (+50 pts) for {symbol} ({ticket})")
                self.mt5.modify_position_sl(ticket, price_open, tp_current)

            # 2. Aggressive Trailing: 10-point trail once safe (sl != 0)
            elif sl_current != 0:
                new_sl = 0
                if pos.type == 0: # BUY
                    # If current price is > 10 points above current SL, move SL up
                    if price_current - sl_current > 10 * symbol_info.point:
                        new_sl = price_current - 10 * symbol_info.point
                else: # SELL
                    # If current price is < 10 points below current SL, move SL down
                    if sl_current - price_current > 10 * symbol_info.point:
                        new_sl = price_current + 10 * symbol_info.point

                if new_sl != 0:
                    logger.info(f"TRAIL: Moving SL for {symbol} to lock in profit.")
                    success = self.mt5.modify_position_sl(ticket, new_sl, tp_current)
                    if not success:
                         # Check if failure was due to AutoTrading (10017)
                         import MetaTrader5 as mt5_lib
                         if mt5_lib.last_error()[0] == 10017:
                             logger.warning("Modify SL failed (AutoTrading Disabled). Waiting 60s before retry.")
                             self._last_sl_error_time = time.time()
                             break

    def execute_signal(self, signal, balance, target=50.0):
        """Returns True if Retcode 10027 is detected"""
        try:
            import MetaTrader5 as mt5_lib
        except ImportError:
            mt5_lib = self.mt5.mt5 # Fallback to client's library reference

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
        logger.info(f"[ATTEMPT] Trying to {side} {instrument} with {units} lots...")
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
            return False
        else:
            error_info = mt5_lib.last_error()
            # If error info is a tuple, the code is first element
            error_code = error_info[0] if isinstance(error_info, (tuple, list)) else error_info
            logger.error(f"[ATTEMPT] Failed to {side} {instrument} | Reason: MT5 Error {error_info}")

            # Return True if AutoTrading disabled (10027 or 10017)
            if error_code in [10027, 10017]:
                return True
            return False
