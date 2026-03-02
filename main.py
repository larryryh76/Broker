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

        # Execution Loop (Fantasy Execution)
        # Note: In GitHub Actions, we run for a limited time
        import time
        start_time = time.time()
        while time.time() - start_time < 240: # Run for 4 minutes
            # Recalculate Virtual Equity and Target for real-time logging
            target, virtual_equity, day, multiplier = update_day_and_get_target(mt5, db)

            # Hard Reset: If virtual_equity < $0.50
            if virtual_equity < 0.50:
                logger.error("VIRTUAL ACCOUNT BLOWN")
                db.clear_learning_state()
                sys.exit(1)

            # Visual Logging Format
            logger.info(f"[TRAINING] Day: {day} | Virtual Equity: ${virtual_equity:.2f} | Target: ${target:.2f} | Multiplier: {multiplier}x")

            # 1. Manage Open Positions (Zero-Risk & Trailing)
            executor.manage_open_positions()

            # 2. Run Strategy Cycle
            executor.run_cycle(config.INSTRUMENTS, target=target, virtual_balance=virtual_equity)

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
    import random
    DEMO_BASE = 10000000.00

    # Virtualization Logic
    account = mt5.get_account_summary()
    if not account:
        return 50.0, 5.0, 1, 0

    real_balance = float(account["balance"])
    virtual_equity = (real_balance - DEMO_BASE) + 5.00

    latest_state = db.get_latest_learning_state()
    multiplier = 0

    if virtual_equity < 50.00:
        day = 1
        target = 50.00
    else:
        day = 2
        # Use one-time random multiplier from persistent state or generate new
        if latest_state and latest_state.get("day_count") == 2 and latest_state.get("multiplier"):
            multiplier = latest_state.get("multiplier")
        else:
            multiplier = random.randint(4, 10)
        target = 50.00 * multiplier

    return target, virtual_equity, day, multiplier

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

    # Retrieve current day and multiplier
    target, virtual_equity, day, multiplier = update_day_and_get_target(mt5, db)

    state_data = {
        "balance": balance,
        "virtual_equity": virtual_equity,
        "daily_pnl": daily_pnl,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "instrument_performance": instrument_perf,
        "initial_daily_balance": initial_daily_balance,
        "day_count": day,
        "multiplier": multiplier
    }

    db.save_learning_state(state_data)
    logger.info(f"Learning state updated. Daily P&L: ${daily_pnl:.2f}, Win Rate: {win_rate:.2f}%")

if __name__ == "__main__":
    main()
