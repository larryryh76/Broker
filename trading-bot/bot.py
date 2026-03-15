import config
import MetaTrader5 as mt5
from terminal_connector import TerminalConnector
from db_client import DBClient
from data_engine import DataEngine
from strategy import Strategy
from ai_model import AIModel
from risk_management import RiskManagement
import time
import os
import json
import random
from datetime import datetime, timezone

class FoundationBot:
    def __init__(self):
        for d in ["logs", "trades", "snapshots"]:
            os.makedirs(os.path.join(config.BASE_DIR, d), exist_ok=True)

        self.db = DBClient()
        self.connector = TerminalConnector()
        self.data_engine = DataEngine(self.connector)
        self.strategy = Strategy()
        self.ai_model = AIModel(db_client=self.db)
        self.risk_manager = None # Will be initialized per cycle with account info

    def log(self, message, category="foundation"):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(config.LOG_DIR, f"{category}.log")
        with open(log_file, "a") as f:
            f.write(f"[{ts}] {message}\n")
        print(f"[{category}] {message}")

    def reconcile_trades(self):
        """Syncs broker history with MongoDB and calculates realized profit."""
        self.log("Reconciling closed deals...")
        deals = self.connector.get_closed_deals()
        for deal in deals:
            # Sync deal to DB if not already present
            self.db.update_trade(deal['order'], {
                "status": "CLOSED",
                "profit_loss": deal['profit'],
                "close_time": datetime.fromtimestamp(deal['time'], tz=timezone.utc).isoformat()
            })

        realized_profit = self.db.get_total_realized_profit()
        self.log(f"Total Realized Bot Profit: ${realized_profit:.2f}")
        return realized_profit

    def log_snapshot(self, snapshot):
        """Saves account snapshot to a specific text file for auditing."""
        snap_text = f"[{snapshot['timestamp']}] Balance: ${snapshot['balance']} | Equity: ${snapshot['equity']} | Margin: ${snapshot['margin']}\n"
        snap_log_path = os.path.join(config.LOG_DIR, "account_snapshot.txt")
        with open(snap_log_path, "a") as f:
            f.write(snap_text)

    def run_trading_cycle(self):
        self.log("--- STARTING AUTONOMOUS TRADING CYCLE ---")

        if not self.connector.connect():
            self.log("INITIALIZATION FAILURE. EXCELSIOR.")
            return

        try:
            # 1. Reconciliation & Virtual Equity
            realized_profit = self.reconcile_trades()
            virtual_equity = config.INITIAL_CAPITAL + realized_profit

            # 2. Account Info & Risk Management
            account = self.connector.get_account_info()
            if not account:
                self.log("CRITICAL: Failed to retrieve account info.")
                return

            self.risk_manager = RiskManagement(account, virtual_equity)

            # Daily Drawdown Check
            state = self.db.get_latest_state()
            daily_start_equity = state.get("daily_start_equity", virtual_equity) if state else virtual_equity

            # Simple daily equity reset logic (if first run of the day)
            now = datetime.now(timezone.utc)
            if state and "snapshot" in state and "timestamp" in state["snapshot"]:
                last_ts_str = state["snapshot"]["timestamp"]
                try:
                    last_ts = datetime.fromisoformat(last_ts_str)
                    if last_ts.date() < now.date():
                        daily_start_equity = virtual_equity
                        self.log("New day detected. Resetting daily start equity.")
                except ValueError:
                    pass

            if self.risk_manager.check_circuit_breaker(daily_start_equity):
                self.log("CIRCUIT BREAKER TRIGGERED: Daily drawdown limit reached. Halting.")
                return

            # 3. Snapshot
            snapshot = {
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "balance": account.get("balance"),
                "equity": account.get("equity"),
                "margin": account.get("margin"),
                "margin_free": account.get("margin_free"),
                "virtual_equity": virtual_equity,
                "daily_start_equity": daily_start_equity
            }
            self.log_snapshot(snapshot)
            self.db.save_state({"snapshot": snapshot, "daily_start_equity": daily_start_equity})

            # 4. Position Management (Signal Reversal & Break-Even)
            open_positions = self.connector.get_open_positions()
            for pos in open_positions:
                symbol = pos['symbol']
                df = self.data_engine.download_data(symbol, config.DEFAULT_TIMEFRAME)
                if df is not None:
                    df = self.strategy.calculate_indicators(df)
                    bull_prob, bear_prob = self.ai_model.predict(df)
                    signal, _ = self.strategy.generate_signal(df, bull_prob, bear_prob)

                    # Signal Reversal Closure
                    if (pos['type'] == 0 and signal == "SELL") or (pos['type'] == 1 and signal == "BUY"):
                        self.log(f"REVERSAL DETECTED for {symbol}. Closing position.")
                        self.connector.close_position(pos['ticket'])
                        continue

                    # Break-Even Protection: Move SL to entry after $0.05 profit
                    if pos['profit'] >= 0.05:
                        entry = pos['price_open']
                        if pos['sl'] != entry:
                            self.log(f"Applying BREAK-EVEN to {symbol} (Profit: ${pos['profit']})")
                            self.connector.modify_sl(pos['ticket'], entry, pos['tp'])

            # 5. Opportunity Scanning
            if len(open_positions) < config.MAX_OPEN_POSITIONS:
                for symbol in config.SYMBOLS:
                    if any(p['symbol'] == symbol for p in open_positions):
                        continue # One trade per symbol rule

                    df = self.data_engine.download_data(symbol, config.DEFAULT_TIMEFRAME)
                    if df is None: continue

                    df = self.strategy.calculate_indicators(df)
                    bull_prob, bear_prob = self.ai_model.predict(df)
                    signal, confidence = self.strategy.generate_signal(df, bull_prob, bear_prob)

                    if signal in ["BUY", "SELL"]:
                        self.log(f"SIGNAL: {signal} on {symbol} (Conf: {confidence})")

                        # Stealth Execution Delay
                        delay = random.randint(30, 290)
                        self.log(f"Stealth Mode: Waiting {delay}s before execution...")
                        time.sleep(delay)

                        lot = self.risk_manager.calculate_lot_size(1) # Day param not strictly used in current logic
                        mapped_symbol = self.connector.map_symbol(symbol)
                        tick = mt5.symbol_info_tick(mapped_symbol)
                        if tick is None:
                            self.log(f"CRITICAL: Could not get tick info for {mapped_symbol}")
                            continue

                        current_price = tick.ask if signal == "BUY" else tick.bid
                        atr = df.iloc[-1]['ATR']
                        sl, tp = self.risk_manager.get_levels(signal, current_price, atr)

                        res = self.connector.execute_order(symbol, signal, lot, sl, tp)
                        if res and res.retcode == mt5.TRADE_RETCODE_DONE:
                            self.log(f"SUCCESS: {signal} {lot} {symbol} at {current_price}")
                            self.db.log_trade({
                                "order_id": res.order,
                                "symbol": symbol,
                                "side": signal,
                                "lot": lot,
                                "entry": current_price,
                                "sl": sl,
                                "tp": tp,
                                "status": "OPEN"
                            })
                        else:
                            self.log(f"FAILED to execute {signal}: {res.comment if res else 'Unknown error'}")

                    if len(self.connector.get_open_positions()) >= config.MAX_OPEN_POSITIONS:
                        break

        except Exception as e:
            self.log(f"CYCLE ERROR: {e}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            self.connector.disconnect()
            self.log("--- AUTONOMOUS CYCLE COMPLETE. ---")

if __name__ == "__main__":
    bot = FoundationBot()
    bot.run_trading_cycle()
