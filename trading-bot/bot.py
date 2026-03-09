import config
from terminal_connector import TerminalConnector
from ai_model import AIModel
from risk_management import RiskManagement
from strategy import Strategy
from db_client import DBClient
from mt5_config_injector import inject_headless_config
import time
import os
import random
import requests
import pandas as pd
from datetime import datetime, timezone

class TradingBot:
    def __init__(self):
        inject_headless_config()
        self.db = DBClient()
        self.connector = TerminalConnector()
        self.ai_model = AIModel(db_client=self.db)
        self.strategy = Strategy()
        self.risk_manager = None
        self.current_day = 1
        self.virtual_equity = config.INITIAL_CAPITAL

    def log(self, message):
        if not os.path.exists(config.LOG_DIR): os.makedirs(config.LOG_DIR)
        log_file = os.path.join(config.LOG_DIR, "engine.log")
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        with open(log_file, "a") as f: f.write(f"[{ts}] {message}\n")
        print(f"[{ts}] {message}")

    def run_trading_cycle(self):
        # 1. State Recovery
        latest = self.db.get_latest_state()
        if latest:
            self.current_day = latest.get("day_count", 1)
            self.virtual_equity = config.INITIAL_CAPITAL + self.db.get_total_realized_profit()
            self.log(f"STATE RESTORED: Day {self.current_day} | Virtual Equity: ${self.virtual_equity:.2f}")

        # 2. Connection
        if not self.connector.connect():
            self.log("MT5 CONNECTION FAILURE.")
            return

        try:
            account = self.connector.get_account_info()
            if not account: return

            self.reconcile_trades()
            self.virtual_equity = config.INITIAL_CAPITAL + self.db.get_total_realized_profit()

            if self.virtual_equity < 0.50:
                self.log("HARD RESET TRIGGERED.")
                self.db.clear_all_trades()
                self.db.clear_learning_state()
                self.virtual_equity = config.INITIAL_CAPITAL
                self.current_day = 1

            self.risk_manager = RiskManagement(account, self.virtual_equity)
            initial_daily = latest.get("virtual_equity", self.virtual_equity) if latest else self.virtual_equity
            if self.risk_manager.check_circuit_breaker(initial_daily):
                self.log("CIRCUIT BREAKER ACTIVE.")
                return

            self.manage_trades()

            for sym in config.SYMBOLS:
                self.process_symbol(sym)

            self.snapshot(account)

        except Exception as e:
            self.log(f"ENGINE ERROR: {e}")
        finally:
            self.connector.disconnect()

    def reconcile_trades(self):
        open_logged_trades = self.db.get_open_logged_trades()
        if not open_logged_trades: return
        closed_deals = self.connector.get_closed_deals()
        exit_deals = {str(d["order"]): d for d in closed_deals if d["entry"] == 1}
        for trade in open_logged_trades:
            order_id = str(trade.get("order_id"))
            if order_id in exit_deals:
                deal = exit_deals[order_id]
                self.db.update_trade(order_id, {
                    "status": "CLOSED", "profit_loss": float(deal.get("profit", 0)),
                    "exit_price": deal.get("price"), "exit_time": time.time()
                })

    def manage_trades(self):
        positions = self.connector.get_open_positions()
        for p in positions:
            if p["profit"] > 0.05:
                self.connector.modify_sl(p["ticket"], p["price_open"], p["tp"])
            df = self.connector.get_candles(p["symbol"], config.DEFAULT_TIMEFRAME)
            if df is not None and not df.empty:
                df = self.strategy.calculate_indicators(df)
                bull, bear = self.ai_model.predict(df)
                signal, _ = self.strategy.generate_signal(df, bull, bear)
                if (p["type"] == 0 and signal == "SELL") or (p["type"] == 1 and signal == "BUY"):
                    self.connector.close_position(p["ticket"])

    def process_symbol(self, symbol):
        df = self.connector.get_candles(symbol, config.DEFAULT_TIMEFRAME)
        if df is None or df.empty: return
        df = self.strategy.calculate_indicators(df)
        if not self.ai_model.is_trained: self.ai_model.train(df)
        bull, bear = self.ai_model.predict(df)
        signal, confidence = self.strategy.generate_signal(df, bull, bear)
        self.log(f"SCAN: {symbol} | Signal: {signal}")
        if signal in ["BUY", "SELL"]:
            if len(self.connector.get_open_positions()) >= config.MAX_OPEN_POSITIONS: return
            delay = random.randint(30, 290)
            time.sleep(delay)
            lot = self.risk_manager.calculate_lot_size(self.current_day)
            entry = df.iloc[-1]['close']
            sl, tp = self.risk_manager.get_levels(signal, entry, df.iloc[-1]['ATR'])
            res = self.connector.execute_order(symbol, signal, lot, sl, tp)
            if res:
                self.db.log_trade({
                    "symbol": symbol, "side": signal, "profit_loss": 0.0,
                    "status": "OPEN", "order_id": res.order, "confidence": confidence
                })

    def snapshot(self, account):
        realized = self.db.get_total_realized_profit()
        self.virtual_equity = config.INITIAL_CAPITAL + realized
        for i, target in enumerate(config.TARGET_MULTIPLIER_SEQUENCE):
             if self.virtual_equity >= target: self.current_day = i + 2
        self.db.save_state({
            "day_count": self.current_day, "virtual_equity": self.virtual_equity,
            "broker_balance": account["balance"]
        })

    def trigger_auto_restart(self):
        # SECTION 5 — Auto Restart After Job Finishes
        repo = os.getenv("GITHUB_REPOSITORY")
        token = os.getenv("GITHUB_TOKEN")
        if repo and token:
            self.log("Triggering auto-restart workflow...")
            requests.post(
                f"https://api.github.com/repos/{repo}/actions/workflows/trading-bot.yml/dispatches",
                headers={"Authorization": f"token {token}"},
                json={"ref": "main"}
            )

    def main_loop(self):
        # SECTION 6 — Fail Safe Watchdog Loop
        self.log("Entering Fail-Safe Watchdog Loop.")
        start_time = time.time()
        # Run for approx 4.5 hours before triggering restart if on GHA
        limit = 4.5 * 3600

        while True:
            try:
                self.run_trading_cycle()

                # Check for workflow timeout (approx 5 hours)
                if os.getenv("GITHUB_ACTIONS") == "true":
                    if time.time() - start_time > limit:
                        self.trigger_auto_restart()
                        break

            except Exception as e:
                self.log(f"Cycle Error: {e}")
                time.sleep(60)

            time.sleep(300) # Wait 5 minutes between scans

if __name__ == "__main__":
    bot = TradingBot()
    bot.main_loop()
