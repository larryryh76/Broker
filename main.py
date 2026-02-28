import sys
from config import validate_config, INSTRUMENTS, logger
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
        db = DBClient()
        strategy = Strategy()
        executor = Executor(mt5, db, strategy)

        # Run one cycle
        executor.run_cycle(INSTRUMENTS)

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
        "initial_daily_balance": initial_daily_balance
    }

    db.save_learning_state(state_data)
    logger.info(f"Learning state updated. Daily P&L: ${daily_pnl:.2f}, Win Rate: {win_rate:.2f}%")

if __name__ == "__main__":
    main()
