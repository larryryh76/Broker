import sys
import time
import random
from config import logger, DAILY_DRAWDOWN_LIMIT

class Executor:
    def __init__(self, mt5_client, db_client, strategy):
        self.mt5 = mt5_client
        self.db = db_client
        self.strategy = strategy
        self._last_api_action = {} # Symbol based cooldowns
        self._last_sl_move_time = 0 # DEPRECATED
        self._idle_cycles = 0

    def check_circuit_breaker(self, virtual_equity):
        latest_state = self.db.get_latest_learning_state()
        if not latest_state:
            return False

        from datetime import datetime, timezone
        state_time = latest_state["timestamp"]
        if state_time.tzinfo is None:
            state_time = state_time.replace(tzinfo=timezone.utc)

        # Only apply circuit breaker if the state is from today
        if state_time.date() == datetime.now(timezone.utc).date():
            initial_daily_virtual_equity = latest_state.get("initial_daily_virtual_equity", virtual_equity)
            if initial_daily_virtual_equity <= 0:
                return False

            drawdown = (initial_daily_virtual_equity - virtual_equity) / initial_daily_virtual_equity

            if drawdown >= DAILY_DRAWDOWN_LIMIT:
                logger.warning(f"CIRCUIT BREAKER ACTIVATED: Drawdown is {drawdown*100:.2f}% (Limit: {DAILY_DRAWDOWN_LIMIT*100}%)")
                return True
        return False

    def run_cycle(self, instruments, target=50.0, virtual_balance=5.0, active_level=5.0):
        # DAILY EXECUTION ENFORCEMENT
        # Track consecutive idle cycles across sessions via DB
        latest_state = self.db.get_latest_learning_state()
        db_idle_scans = latest_state.get("consecutive_idle_scans", 0) if latest_state else 0
        total_idle = self._idle_cycles + db_idle_scans

        # Relaxed mode check: Escalating urgency if no trades executed
        is_relaxed = total_idle > 3
        if is_relaxed:
            logger.info(f"Execution Urgency HIGH (Idle cycles: {total_idle}). Thresholds RELAXED.")

        # 0. Daily Momentum Check (Dynamic target protection)
        # If objective reached, stop trading to secure the growth curve.
        if virtual_balance >= target:
            logger.info(f"DAILY OBJECTIVE SECURED (${virtual_balance:.2f} >= ${target:.2f}). HALTING OPERATION.")
            return False

        logger.info("Scanning for opportunities...")

        # Asset Prioritization for Phase 1
        if virtual_balance < 50.0:
            priority = ["EURUSDm", "GBPJPYm"]
            # Move priority instruments to the front
            instruments = priority + [inst for inst in instruments if inst not in priority]

        # Verification: Check trade permissions
        if not self.mt5.connect():
             logger.error("MT5 connection failed.")
             return

        # Check if trading is allowed globally
        self.mt5.check_trade_allowed()

        # 0. Recursive Learning Adjustment
        latest_state = self.db.get_latest_learning_state()
        if latest_state:
            self.strategy.adjust_parameters(latest_state)

        # 1. Initialization
        account = self.mt5.get_account_summary()
        if not account:
            return

        if self.check_circuit_breaker(virtual_balance):
            logger.info("Trading halted due to circuit breaker.")
            return

        # 1.5 Check for open positions
        open_positions = self.mt5.get_open_trades()
        pos_counts = {}
        for p in open_positions:
            pos_counts[p["symbol"]] = pos_counts.get(p["symbol"], 0) + 1

        # 2. Market Data and Signal Generation
        signals = []
        for instrument in instruments:
            # Limit simultaneous trades per symbol to a maximum of 3
            if pos_counts.get(instrument, 0) >= 3:
                continue

            # Spread Check (Pre-Scan for efficiency)
            symbol_info = self.mt5.symbol_info(instrument)
            tick = self.mt5.symbol_info_tick(instrument)
            if not symbol_info or not tick:
                continue

            # Fetch Daily ATR for Volatility Filter
            import MetaTrader5 as mt5_lib
            daily_candles = self.mt5.get_candles(instrument, count=20, timeframe=mt5_lib.TIMEFRAME_D1)
            if not daily_candles:
                continue

            df_daily = self.strategy.prepare_data(daily_candles)
            atr = self.strategy.calculate_atr(df_daily)

            spread = tick.ask - tick.bid
            if atr:
                # Volatility Filter: Spread must be less than 10% of Daily ATR
                if spread > (0.10 * atr):
                    logger.warning(f"Skipping {instrument} - High Volatility (Spread {spread:.5f} > 10% ATR {atr:.5f})")
                    continue
            else:
                # Fallback to absolute point spread check if ATR unavailable
                spread_points = spread / symbol_info.point
                if spread_points > 20:
                    continue

            candles = self.mt5.get_candles(instrument)
            if not candles:
                continue

            df = self.strategy.prepare_data(candles)
            df = self.strategy.calculate_indicators(df, df_d1=df_daily)

            # Fetch H1 data for signal generation intelligence
            h1_candles = self.mt5.get_candles(instrument, count=50, timeframe=mt5_lib.TIMEFRAME_H1)
            df_h1 = self.strategy.prepare_data(h1_candles) if h1_candles else None

            signal = self.strategy.generate_signal(df, instrument=instrument, df_h1=df_h1, relaxed=is_relaxed)

            if signal and signal["side"] != "SKIP":
                # Dynamic Margin Check
                import MetaTrader5 as mt5_lib
                order_type = mt5_lib.ORDER_TYPE_BUY if signal["side"] == "BUY" else mt5_lib.ORDER_TYPE_SELL
                # Sizing is based EXCLUSIVELY on the Active Virtual Capital Level
                volume = self.strategy.calculate_position_size(active_level, instrument=instrument, target=target)

                if volume <= 0:
                    continue # Locked or invalid

                required_margin = self.mt5.calculate_margin(instrument, order_type, volume, signal["price"])

                if required_margin:
                    # If margin required is > 80% of current Virtual Equity, skip/look for cheaper pair
                    if required_margin > (0.80 * virtual_balance):
                        logger.warning(f"Skipping {instrument} - Margin too high (${required_margin:.2f} > 80% of Equity ${virtual_balance:.2f})")
                        continue

                signal["instrument"] = instrument
                signals.append(signal)
                logger.info(f"ALGO SIGNAL: {instrument} {signal['side']} @ {signal['price']} (Spread: {spread:.5f}, ATR: {atr if atr else 0:.5f})")

        # 3. Decision Authority Override: Scaling with Outcome Dominance
        error_detected = False
        executed_in_cycle = False

        # Strict Global Position Limit: ONE trade at a time
        # Intelligence is measured by closed profitable outcomes, not volume.
        total_open = sum(pos_counts.values())

        # DAILY EXECUTION ENFORCEMENT: Force action if urgency is extreme
        force_action = total_idle > 10 and total_open == 0

        if total_open >= 1:
            return False

        for signal in signals:
            inst = signal["instrument"]

            if self.execute_signal(signal, virtual_balance, target=target, active_level=active_level):
                error_detected = True
            else:
                executed_in_cycle = True
                pos_counts[inst] = pos_counts.get(inst, 0) + 1
                # Entry Cooling: Symbol-specific
                self._last_api_action[inst] = time.time()
                logger.info(f"Entry Secured for {inst}. Objective scaling active.")

        if executed_in_cycle:
            self._idle_cycles = 0
            # Reset DB counter on success
            latest_state = self.db.get_latest_learning_state()
            if latest_state:
                self.db.learning_state_collection.update_one(
                    {"_id": latest_state["_id"]},
                    {"$set": {"consecutive_idle_scans": 0}}
                )
        else:
            self._idle_cycles += 1
            # Update DB counter
            latest_state = self.db.get_latest_learning_state()
            if latest_state:
                self.db.learning_state_collection.update_one(
                    {"_id": latest_state["_id"]},
                    {"$inc": {"consecutive_idle_scans": 1}}
                )

        return error_detected

    def manage_open_positions(self, virtual_equity=5.0):
        """
        Intelligent Management: Exit Analysis & Stop Discipline
        """
        # Rate-limiting for AutoTrading errors
        if hasattr(self, '_last_sl_error_time'):
            if time.time() - self._last_sl_error_time < 60:
                return

        positions = self.mt5.get_open_trades()
        for p in positions:
            symbol = p["symbol"]
            ticket = p["ticket"]

            # Intelligence Filter: 10s cooldown per symbol
            if time.time() - self._last_api_action.get(symbol, 0) < 10:
                continue

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

            # 0. Intelligent Exit Analysis
            # Recalculate indicators for the open symbol
            candles = self.mt5.get_candles(symbol, count=100)
            df = self.strategy.prepare_data(candles)
            df = self.strategy.calculate_indicators(df)

            # Score dominance for current position side
            dominance_score = 0.0
            if df is not None:
                latest = df.iloc[-1]
                if pos.type == 0: # BUY
                    if latest["rsi"] < 35: dominance_score += 1.0
                    if latest["ma_fast"] > latest["ma_slow"]: dominance_score += 1.0
                    if latest["close"] <= latest["bb_lower"]: dominance_score += 1.0
                else: # SELL
                    if latest["rsi"] > 65: dominance_score += 1.0
                    if latest["ma_fast"] < latest["ma_slow"]: dominance_score += 1.0
                    if latest["close"] >= latest["bb_upper"]: dominance_score += 1.0

            should_close, reason = self.strategy.analyze_exit(symbol, pos.profit, dominance_score, virtual_equity)
            if should_close:
                logger.info(f"INTELLIGENT EXIT: Closing {symbol} ({ticket}) | Reason: {reason} | Profit: ${pos.profit:.2f}")
                if self.mt5.close_position(ticket):
                    self._last_api_action[symbol] = time.time()
                continue

            # Current distance from open in points
            dist_from_open = (price_current - price_open) / symbol_info.point if pos.type == 0 else (price_open - price_current) / symbol_info.point

            # 1. No-Loss Protocol: The $0.05 Safety Switch
            if pos.profit >= 0.05 and (sl_current == 0 or abs(sl_current - price_open) < symbol_info.point * 0.5):
                # Calculate SL for +$0.01 profit
                offset = symbol_info.point
                sl_be = price_open + offset if pos.type == 0 else price_open - offset

                logger.info(f"$0.05 SAFETY SWITCH: Moving SL to +1 pt (+$0.01) for {symbol} ({ticket})")
                if self.mt5.modify_position_sl(ticket, sl_be, tp_current):
                    self._last_api_action[symbol] = time.time()

            # 2. Aggressive Trailing: 10-point trail once safe (sl != 0)
            elif sl_current != 0:
                new_sl = 0
                # Meaningful Margin Discipline: Only move SL if improvement > 5 points
                min_improvement = 5 * symbol_info.point

                if pos.type == 0: # BUY
                    # If current price is > 10 points above current SL, move SL up
                    candidate_sl = price_current - 10 * symbol_info.point
                    if candidate_sl > sl_current + min_improvement:
                        new_sl = candidate_sl
                else: # SELL
                    # If current price is < 10 points below current SL, move SL down
                    candidate_sl = price_current + 10 * symbol_info.point
                    if candidate_sl < sl_current - min_improvement:
                        new_sl = candidate_sl

                if new_sl != 0:
                    logger.info(f"TRAIL: Moving SL for {symbol} to lock in profit (Improvement: {abs(new_sl - sl_current) / symbol_info.point:.1f} pts)")
                    success = self.mt5.modify_position_sl(ticket, new_sl, tp_current)
                    if success:
                        self._last_api_action[symbol] = time.time()
                    else:
                         # Check if failure was due to AutoTrading (10017)
                         import MetaTrader5 as mt5_lib
                         if mt5_lib.last_error()[0] == 10017:
                             logger.warning("Modify SL failed (AutoTrading Disabled). Waiting 60s before retry.")
                             self._last_sl_error_time = time.time()
                             break

    def execute_signal(self, signal, balance, target=50.0, active_level=5.0):
        """Returns True if Retcode 10027 is detected"""
        try:
            import MetaTrader5 as mt5_lib
        except ImportError:
            mt5_lib = self.mt5.mt5 # Fallback to client's library reference

        instrument = signal["instrument"]
        side = signal["side"]
        price = signal["price"]
        confidence = signal["confidence"]

        # 4. Risk Assessment & Levels
        stop_loss, take_profit = self.strategy.calculate_levels(side, price)

        # 5. Position Sizing
        # Sizing is based EXCLUSIVELY on the Active Virtual Capital Level
        units = self.strategy.calculate_position_size(active_level, instrument=instrument, target=target)

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
