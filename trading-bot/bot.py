import config
from terminal_connector import TerminalConnector
from db_client import DBClient
import time
import os
import json
from datetime import datetime, timezone

class FoundationBot:
    def __init__(self):
        for d in ["logs", "trades", "snapshots"]:
            os.makedirs(os.path.join(config.BASE_DIR, d), exist_ok=True)

        self.db = DBClient()
        self.connector = TerminalConnector()

    def log(self, message, category="foundation"):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(config.LOG_DIR, f"{category}.log")
        with open(log_file, "a") as f:
            f.write(f"[{ts}] {message}\n")
        print(f"[{category}] {message}")

    def run_snapshot_cycle(self):
        self.log("--- STARTING FOUNDATION SNAPSHOT ---")

        # Connect
        if not self.connector.connect():
            self.log("INITIALIZATION FAILURE. EXCELSIOR.")
            return

        try:
            account = self.connector.get_account_info()
            if not account:
                self.log("CRITICAL: Failed to retrieve account info.")
                return

            # Implementation for minimal foundation
            snapshot = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "balance": account.get("balance"),
                "equity": account.get("equity"),
                "margin": account.get("margin"),
                "margin_free": account.get("margin_free"),
                "leverage": account.get("leverage")
            }

            # Save local snapshot
            snap_path = os.path.join(config.BASE_DIR, "snapshots", f"account_{int(time.time())}.json")
            with open(snap_path, "w") as f:
                json.dump(snapshot, f, indent=4)

            self.log(f"ACCOUNT: Balance: ${snapshot['balance']} | Equity: ${snapshot['equity']}")

            # Persistence (MongoDB if configured, otherwise logs)
            try:
                self.db.save_state({"snapshot": snapshot})
                self.log("Cloud state updated.")
            except Exception as e:
                self.log(f"DB Warning: {e}")

        except Exception as e:
            self.log(f"SNAPSHOT ERROR: {e}")
        finally:
            self.connector.disconnect()
            self.log("--- FOUNDATION CYCLE COMPLETE. ---")

if __name__ == "__main__":
    bot = FoundationBot()
    bot.run_snapshot_cycle()
