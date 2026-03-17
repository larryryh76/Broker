import config
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

class TradingMachine:
    def __init__(self):
        for d in ["logs", "trades", "snapshots"]:
            os.makedirs(os.path.join(config.BASE_DIR, d), exist_ok=True)

        self.db = DBClient()
        self.connector = TerminalConnector()
        self.data_engine = DataEngine(self.connector)
        self.strategy = Strategy()
        self.ai_model = AIModel(db_client=self.db)
        self.risk_manager = None # Initialized per cycle

    def log(self, message, category="machine"):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(config.LOG_DIR, f"{category}.log")
        with open(log_file, "a") as f:
            f.write(f"[{ts}] {message}\n")
        print(f"[{category}] {message}")

    def reconcile_trades(self):
        """Syncs broker history with MongoDB and updates realized profit."""
        self.log("Syncing trade history with cloud state...")
        deals = self.connector.get_closed_deals()
        for deal in deals:
            self.db.update_trade(deal['order'], {
                "status": "CLOSED",
                "profit_loss": deal['profit'],
                "close_time": datetime.fromtimestamp(deal['time'], tz=timezone.utc).isoformat()
            })

        realized_profit = self.db.get_total_realized_profit()
        self.log(f"Cumulative Bot Profit: ${realized_profit:.2f}")
        return realized_profit

    def run_cycle(self):
        self.log("--- STARTING AUTONOMOUS TRADING CYCLE ---")

        if not self.connector.connect():
            self.log("CRITICAL: Bridge initialization failed. Terminating cycle.")
            return

        try:
            # 1. State Analysis
            realized_profit = self.reconcile_trades()
            virtual_equity = config.INITIAL_CAPITAL + realized_profit

            account = self.connector.get_account_info()
            if not account:
                self.log("CRITICAL: Failed to retrieve account metadata.")
                return

            self.risk_manager = RiskManagement(account, virtual_equity)

            # Daily Drawdown Protection
            state = self.db.get_latest_state()
            daily_start_equity = state.get("daily_start_equity", virtual_equity) if state else virtual_equity

            now = datetime.now(timezone.utc)
            if state and "snapshot" in state and "timestamp" in state["snapshot"]:
                last_ts = datetime.fromisoformat(state["snapshot"]["timestamp"])
                if last_ts.date() < now.date():
                    daily_start_equity = virtual_equity
                    self.log("New trading day detected. Calibrating daily circuit breaker.")

            if self.risk_manager.check_circuit_breaker(daily_start_equity):
                self.log("CIRCUIT BREAKER: Daily drawdown limit reached. Trading halted.")
                return

            # 2. Account Snapshot
            snapshot = {
                "timestamp": now.isoformat(),
                "balance": account.get("balance"),
                "equity": account.get("equity"),
                "virtual_equity": virtual_equity,
                "daily_start_equity": daily_start_equity
            }
            self.db.save_state({"snapshot": snapshot, "daily_start_equity": daily_start_equity})

            snap_text_path = os.path.join(config.LOG_DIR, "account_snapshot.txt")
            with open(snap_text_path, "a") as f:
                f.write(f"[{snapshot['timestamp']}] Balance: ${snapshot['balance']} | Equity: ${snapshot['equity']} | Virtual: ${virtual_equity}\n")

            # 3. Position Management (Reversal & Protection)
            open_positions = self.connector.get_open_positions()
            for pos in open_positions:
                symbol = pos['symbol']
                df = self.data_engine.download_data(symbol, config.DEFAULT_TIMEFRAME)
                if df is not None:
                    df = self.strategy.calculate_indicators(df)
                    bull_prob, bear_prob = self.ai_model.predict(df)
                    signal, _ = self.strategy.generate_signal(df, bull_prob, bear_prob)

                    # Immediate Reversal Closure
                    if (pos['type'] == 0 and signal == "SELL") or (pos['type'] == 1 and signal == "BUY"):
                        self.log(f"REVERSAL: Signal flip on {symbol}. Closing position immediately.")
                        self.connector.close_position(pos['ticket'])
                        continue

                    # Break-Even Protection (Trailing SL)
                    if pos['profit'] >= 0.05:
                        entry = pos['price_open']
                        if pos['sl'] != entry:
                            self.log(f"PROTECTION: Securing Break-Even for {symbol}")
                            self.connector.modify_sl(pos['ticket'], entry, pos['tp'])

            # 4. Opportunity Scanning
            if len(open_positions) < config.MAX_OPEN_POSITIONS:
                for symbol in config.SYMBOLS:
                    if any(p['symbol'] == symbol for p in open_positions):
                        continue # Strict "one trade per symbol" policy

                    df = self.data_engine.download_data(symbol, config.DEFAULT_TIMEFRAME)
                    if df is None: continue

                    df = self.strategy.calculate_indicators(df)
                    bull_prob, bear_prob = self.ai_model.predict(df)
                    signal, confidence = self.strategy.generate_signal(df, bull_prob, bear_prob)

                    if signal in ["BUY", "SELL"]:
                        self.log(f"ALERT: {signal} detected on {symbol} (Confidence: {confidence})")

                        # Stealth Execution Delay (Anti-Institution)
                        delay = random.randint(30, 290)
                        self.log(f"Stealth: Postponing submission for {delay}s...")
                        time.sleep(delay)

                        lot = self.risk_manager.calculate_lot_size(1)
                        mapped_symbol = self.connector.map_symbol(symbol)

                        # Refresh tick info after delay
                        tick = self.connector.mt5.symbol_info_tick(mapped_symbol)
                        if tick is None: continue

                        current_price = tick.ask if signal == "BUY" else tick.bid
                        atr = df.iloc[-1]['ATR']
                        sl, tp = self.risk_manager.get_levels(signal, current_price, atr)

                        res = self.connector.execute_order(symbol, signal, lot, sl, tp)
                        if res and res.retcode == self.connector.mt5.TRADE_RETCODE_DONE:
                            self.log(f"SUCCESS: Executed {signal} {lot} {symbol} at {current_price}")
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
                            self.log(f"FAILURE: Order submission failed: {res.comment if res else 'Unknown bridge error'}")

                    if len(self.connector.get_open_positions()) >= config.MAX_OPEN_POSITIONS:
                        break

        except Exception as e:
            self.log(f"CRITICAL MACHINE FAILURE: {e}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            self.connector.disconnect()
            self.log("--- CYCLE COMPLETE. ---")

if __name__ == "__main__":
    machine = TradingMachine()
    machine.run_cycle()
