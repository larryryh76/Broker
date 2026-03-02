import sys
import config
from config import validate_config, logger
from mt5_client import MT5Client
from db_client import DBClient
from strategy import Strategy
from executor import Executor

def main():
    if not validate_config():
        logger.error("Configuration validation failed. Exiting.")
        sys.exit(1)

    logger.info("Initializing The Money Machine...")

    mt5 = MT5Client()
    try:
        if not mt5.connect():
            logger.error("Could not connect to MT5. Exiting.")
            sys.exit(1)

        import MetaTrader5 as mt5_lib
        acc_info = mt5_lib.account_info()
        term_info = mt5_lib.terminal_info()

        if not term_info.trade_allowed or not acc_info.trade_allowed:
            logger.error("CRITICAL ERROR: Algo Trading Disabled")
            sys.exit(1)

        db = DBClient()
        strategy = Strategy()
        executor = Executor(mt5, db, strategy)

        # Calculate Daily Target and Increment Day
        target, virtual_balance = update_day_and_get_target(mt5, db)
        logger.info(f"Virtual Balance: ${virtual_balance:.2f} | Today's Target: ${target:.2f}")

        # Execution Loop (Fantasy Execution)
        # Note: In GitHub Actions, we run for a limited time
        import time
        start_time = time.time()
        while time.time() - start_time < 240: # Run for 4 minutes
            # 1. Manage Open Positions (Zero-Risk & Trailing)
            executor.manage_open_positions()

            # 2. Run Strategy Cycle
            executor.run_cycle(config.INSTRUMENTS, target=target, virtual_balance=virtual_balance)

            # 3. Check for Rotation
            # (Logic handled inside run_cycle based on spread)

            time.sleep(5)

        # After cycle, update learning state
        update_learning_state(mt5, db)

        logger.info("Execution cycle complete.")

    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}", exc_info=True)
        sys.exit(1)
    finally:
        mt5.close()

def reconcile_trades(mt5, db):
    logger.info("Reconciling trades...")
    open_logged_trades = db.get_open_logged_trades()
    if not open_logged_trades:
        return

    closed_oanda_trades = mt5.get_closed_trades()
    closed_dict = {str(t["id"]): t for t in closed_oanda_trades}

    for trade in open_logged_trades:
        order_id = str(trade.get("order_id"))
        if order_id in closed_dict:
            oanda_trade = closed_dict[order_id]
            realized_pl = float(oanda_trade.get("realizedPL", 0))
            exit_price = float(oanda_trade.get("averageClosePrice", 0))

            db.update_trade(order_id, {
                "status": "CLOSED",
                "profit_loss": realized_pl,
                "exit_price": exit_price,
                "exit_time": oanda_trade.get("closeTime")
            })
            logger.info(f"Trade {order_id} reconciled: PL=${realized_pl}")

def update_day_and_get_target(mt5, db):
    import os
    import random
    day_file = "day_count.txt"
    base_training_balance = 5.00

    # Virtualization: $10,000,000 offset for Demo Accounts
    account = mt5.get_account_summary()
    if not account:
        return 50.0, base_training_balance

    real_balance = float(account["balance"])
    # Fantasy virtualization logic
    current_profit = real_balance - 10000000.00

    current_virtual_balance = base_training_balance + current_profit

    # Determine Day and Target
    if current_profit < 50.00:
        day = 1
        target = 50.00
    else:
        day = 2 # Fantasy "Day 2+"
        target = 50.0 * random.randint(4, 10)
        logger.info(f"Quest Progress: Day 2+ Activated. Target Multiplier: {target/50:.0f}x")

    # Sync to local file for reference
    with open(day_file, "w") as f:
        f.write(str(day))

    return target, current_virtual_balance

def get_target_for_day(day, prev_profit=50.0):
    if day == 1:
        return 50.0
    return prev_profit * (day + 2)

def update_learning_state(mt5, db):
    logger.info("Updating learning state...")
    reconcile_trades(mt5, db)

    account = mt5.get_account_summary()
    if not account:
        logger.warning("Could not fetch account summary for learning state update.")
        return

    balance = float(account["balance"])
    # Fetch trades from today that are CLOSED
    from datetime import datetime, timezone
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)

    all_daily_trades = db.get_daily_trades()
    closed_daily_trades = [t for t in all_daily_trades if t.get("status") == "CLOSED"]

    total_trades = len(closed_daily_trades)
    wins = [t for t in closed_daily_trades if t.get("profit_loss", 0) > 0]
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    daily_pnl = sum([t.get("profit_loss", 0) for t in closed_daily_trades])

    # Simple instrument performance tracking
    instrument_perf = {}
    for t in closed_daily_trades:
        inst = t["instrument"]
        if inst not in instrument_perf:
            instrument_perf[inst] = {"wins": 0, "losses": 0}
        if t.get("profit_loss", 0) > 0:
            instrument_perf[inst]["wins"] += 1
        else:
            instrument_perf[inst]["losses"] += 1

    latest_state = db.get_latest_learning_state()

    # Correct daily baseline tracking
    initial_daily_balance = balance
    day = 1 # Default

    if latest_state:
        state_time = latest_state["timestamp"]
        if state_time.tzinfo is None:
            state_time = state_time.replace(tzinfo=timezone.utc)

        # If latest state was today, keep its baseline
        if state_time.date() == datetime.now(timezone.utc).date():
            initial_daily_balance = latest_state.get("initial_daily_balance", balance)
        else:
            # New day, current balance is the new baseline
            initial_daily_balance = balance

    state_data = {
        "balance": balance,
        "daily_pnl": daily_pnl,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "instrument_performance": instrument_perf,
        "initial_daily_balance": initial_daily_balance,
        "day_count": day
    }

    db.save_learning_state(state_data)
    logger.info(f"Learning state updated. Daily P&L: ${daily_pnl:.2f}, Win Rate: {win_rate:.2f}%")

if __name__ == "__main__":
    main()
