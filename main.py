import sys
import os
import time
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

        # Proceeding directly without checks as requested
        db = DBClient()
        strategy = Strategy()
        executor = Executor(mt5, db, strategy)

        # Core Execution Loop
        # Note: In GitHub Actions, we run for a limited time
        start_time = time.time()
        while time.time() - start_time < 240: # Run for 4 minutes
            # Recalculate Virtual Equity and Target for real-time logging
            target, virtual_equity, day, multiplier = update_day_and_get_target(mt5, db)

            # Risk Management: Reset if profit < -$1.50 (Equity < $3.50)
            # Increased threshold as per "Safety Buffer" request
            if virtual_equity < 3.50:
                logger.error("VIRTUAL ACCOUNT BLOWN - HARD RESET")
                db.clear_learning_state()
                # Remove baseline to force restart
                if os.path.exists("baseline.txt"): os.remove("baseline.txt")
                sys.exit(1)

            # Core Performance Monitoring
            if day == 1:
                logger.info("Compounding Session: Phase 1 ($5 -> $50)")
            logger.info(f"[ACTIVE] Virtual Equity: ${virtual_equity:.2f} | Day {day} Goal: ${target:.2f}")

            # 1. Manage Open Positions (Zero-Risk & Trailing)
            executor.manage_open_positions()

            # 2. Run Strategy Cycle
            autotrade_error = executor.run_cycle(config.INSTRUMENTS, target=target, virtual_balance=virtual_equity)

            if autotrade_error:
                logger.warning("AutoTrading error detected. Waiting 10 seconds before next scan...")
                time.sleep(10)

            # 3. Check for Rotation
            # (Logic handled inside run_cycle based on spread)

            time.sleep(5)

        # After cycle, update learning state
        update_learning_state(mt5, db, virtual_equity, day, multiplier)

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

    closed_mt5_trades = mt5.get_closed_trades()
    closed_dict = {str(t["id"]): t for t in closed_mt5_trades}

    for trade in open_logged_trades:
        order_id = str(trade.get("order_id"))
        if order_id in closed_dict:
            mt5_trade = closed_dict[order_id]
            realized_pl = float(mt5_trade.get("realizedPL", 0))
            exit_price = float(mt5_trade.get("averageClosePrice", 0))

            db.update_trade(order_id, {
                "status": "CLOSED",
                "profit_loss": realized_pl,
                "exit_price": exit_price,
                "exit_time": mt5_trade.get("closeTime")
            })
            logger.info(f"Trade {order_id} reconciled: PL=${realized_pl}")

def update_day_and_get_target(mt5, db):
    import random
    import os

    # Virtualization Logic
    account = mt5.get_account_summary()
    if not account:
        return 50.0, 5.0, 1, 0

    real_balance = float(account["balance"])

    # Persistent Baseline Fix for GitHub Actions
    baseline_file = "baseline.txt"
    latest_state = db.get_latest_learning_state()

    if os.path.exists(baseline_file):
        with open(baseline_file, "r") as f:
            INITIAL_DEMO_BALANCE = float(f.read().strip())
    elif latest_state and latest_state.get("initial_demo_balance"):
        # Fallback to MongoDB if baseline.txt was wiped by GHA
        INITIAL_DEMO_BALANCE = latest_state.get("initial_demo_balance")
        with open(baseline_file, "w") as f:
            f.write(str(INITIAL_DEMO_BALANCE))
        logger.info(f"Baseline Restored from MongoDB: {INITIAL_DEMO_BALANCE}")
    else:
        INITIAL_DEMO_BALANCE = real_balance
        with open(baseline_file, "w") as f:
            f.write(str(INITIAL_DEMO_BALANCE))
        logger.info(f"Persistent Baseline Created: {INITIAL_DEMO_BALANCE}")

    # Calculate Profit and Virtual Equity
    profit = real_balance - INITIAL_DEMO_BALANCE
    virtual_equity = profit + 5.00

    latest_state = db.get_latest_learning_state()
    multiplier = 0

    if profit < 50.00:
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

def update_learning_state(mt5, db, virtual_equity, day, multiplier):
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

    # Determine the persistent baseline from file or state
    baseline_file = "baseline.txt"
    if os.path.exists(baseline_file):
        with open(baseline_file, "r") as f:
            initial_demo_balance = float(f.read().strip())
    else:
        latest_state = db.get_latest_learning_state()
        if latest_state and latest_state.get("initial_demo_balance"):
            initial_demo_balance = latest_state.get("initial_demo_balance")
        else:
            initial_demo_balance = balance

    state_data = {
        "balance": balance,
        "virtual_equity": virtual_equity,
        "daily_pnl": daily_pnl,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "instrument_performance": instrument_perf,
        "initial_daily_balance": initial_daily_balance,
        "initial_demo_balance": initial_demo_balance,
        "day_count": day,
        "multiplier": multiplier
    }

    db.save_learning_state(state_data)
    logger.info(f"Learning state updated. Daily P&L: ${daily_pnl:.2f}, Win Rate: {win_rate:.2f}%")

if __name__ == "__main__":
    main()
