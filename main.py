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

    logger.info("--- THE MONEY MACHINE: ULTRA-INTELLIGENT TRADING SYSTEM ---")
    logger.info("[MISSION] Precision trading. Virtual Sub-Capital Model ($5.00).")

    mt5 = MT5Client()
    try:
        if not mt5.connect():
            logger.error("Could not connect to MT5. Exiting.")
            sys.exit(1)

        # Proceeding directly without checks as requested
        db = DBClient()
        strategy = Strategy()
        executor = Executor(mt5, db, strategy)

        # Initial Reconciliation
        reconcile_trades(mt5, db)

        # Core Execution Loop
        # Note: In GitHub Actions, we run for a limited time
        start_time = time.time()
        while time.time() - start_time < 240: # Run for 4 minutes
            # Recalculate Virtual Equity and Target for real-time logging
            target, virtual_equity, day, multiplier = update_day_and_get_target(mt5, db)

            # Risk Management: Reset if equity < $0.50 (90% loss)
            # Threshold set to $0.50 as per "Stop the Panic Reset" objective
            if virtual_equity < 0.50:
                # Check for active positions before reset
                active = mt5.get_open_trades()
                if not active:
                    logger.error("VIRTUAL ACCOUNT BLOWN - HARD RESET")
                    db.clear_learning_state()
                    if os.path.exists("baseline.txt"): os.remove("baseline.txt")
                    sys.exit(1)
                else:
                    logger.warning("Equity low, but trades are active. Holding reset.")

            # Core Performance Monitoring
            if day == 1:
                logger.info("[PHASE 1] Virtual Sub-Capital ($5 -> $50)")
            logger.info(f"[DECISION AUTHORITY] Outcome Dominance Active.")
            logger.info(f"[STATE] Virtual Equity: ${virtual_equity:.2f} | Objective: ${target:.2f} (Day {day})")

            # 1. Manage Open Positions (Intelligent Exit & Stops)
            executor.manage_open_positions(virtual_equity=virtual_equity)

            # 2. Run Strategy Cycle
            autotrade_error = executor.run_cycle(config.INSTRUMENTS, target=target, virtual_balance=virtual_equity, active_level=multiplier)

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
    # CAPITAL ISOLATION: Locked Virtual Sub-Capital
    # Broker balance is ignored. All decision-making uses the $5.00 base.

    realized_profit = db.get_total_realized_profit()
    virtual_equity = 5.00 + realized_profit

    # VIRTUAL CAPITAL PROMOTION & FALLBACK
    # Levels: $5, $50, $250, $1500, $10500... (Discrete approved levels)
    # Target sequence: $50 (Day 1) -> 5x, 6x, 7x, 8x, 9x, 10x
    day1_target = 50.0
    day2_target = day1_target * 5   # $250
    day3_target = day2_target * 6   # $1500
    day4_target = day3_target * 7   # $10500
    day5_target = day4_target * 8   # $84000
    day6_target = day5_target * 9   # $756000
    day7_target = day6_target * 10  # $7.56M

    targets = [day1_target, day2_target, day3_target, day4_target, day5_target, day6_target, day7_target]
    approved_levels = [5.00] + targets

    # Determine ACTIVE Virtual Capital Level
    # Promotion: Earned through performance. Fallback: Reverts if equity drops.
    active_level = 5.00
    for level in approved_levels:
        if virtual_equity >= level:
            active_level = level
        else:
            break

    # Sequential target progression based exclusively on virtual performance
    day = 1
    target = targets[0]
    for i, t in enumerate(targets):
        if virtual_equity >= (t - 0.01):
            day = i + 2
            target = targets[day-1] if day <= len(targets) else targets[-1] * (day + 3)
        else:
            day = i + 1
            target = t
            break

    return target, virtual_equity, day, active_level

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

    # Virtual Sub-Capital Model: Use Virtual Equity for baseline tracking
    initial_daily_virtual_equity = virtual_equity
    consecutive_idle_scans = db.get_idle_scans() if not any(t.get("status") == "CLOSED" for t in all_daily_trades) else 0

    if latest_state:
        state_time = latest_state["timestamp"]
        if state_time.tzinfo is None:
            state_time = state_time.replace(tzinfo=timezone.utc)

        # If latest state was today, keep its virtual baseline
        if state_time.date() == datetime.now(timezone.utc).date():
            initial_daily_virtual_equity = latest_state.get("initial_daily_virtual_equity", virtual_equity)
        else:
            # New day, current virtual equity is the new baseline
            initial_daily_virtual_equity = virtual_equity

    state_data = {
        "balance": balance,
        "virtual_equity": virtual_equity,
        "daily_pnl": daily_pnl,
        "total_trades": total_trades,
        "win_rate": win_rate,
        "instrument_performance": instrument_perf,
        "initial_daily_virtual_equity": initial_daily_virtual_equity,
        "consecutive_idle_scans": consecutive_idle_scans,
        "day_count": day,
        "multiplier": multiplier
    }

    db.save_learning_state(state_data)
    logger.info(f"Learning state updated. Daily P&L: ${daily_pnl:.2f}, Win Rate: {win_rate:.2f}%")

if __name__ == "__main__":
    main()
