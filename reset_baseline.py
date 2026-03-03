from mt5_client import MT5Client
from db_client import DBClient
from config import logger

def reset_baseline():
    mt5 = MT5Client()
    db = DBClient()

    if not mt5.connect():
        print("Could not connect to MT5")
        return

    account = mt5.get_account_summary()
    if not account:
        print("Could not get account summary")
        return

    real_balance = float(account["balance"])

    # We want Virtual Equity to be $5.00
    # virtual_equity = (real_balance - initial_demo_balance) + 5.00
    # To make virtual_equity = 5.00, we need real_balance = initial_demo_balance

    new_state = {
        "balance": real_balance,
        "virtual_equity": 5.00,
        "daily_pnl": 0.00,
        "total_trades": 0,
        "win_rate": 0,
        "instrument_performance": {},
        "initial_daily_balance": real_balance,
        "initial_demo_balance": real_balance,
        "day_count": 1,
        "multiplier": 0
    }

    db.save_learning_state(new_state)

    # Also reset local baseline if it exists (though it will be updated by main.py)
    import os
    if os.path.exists("baseline.txt"):
        with open("baseline.txt", "w") as f:
            f.write(str(real_balance))

    print(f"BASELINE RESET SUCCESSFUL. New baseline: {real_balance}. Virtual Equity: $5.00.")

if __name__ == "__main__":
    reset_baseline()
