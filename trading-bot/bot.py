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
import pandas as pd
from datetime import datetime, timezone

class TradingBot:
    def __init__(self):
        # 1. Environment Prep
        inject_headless_config()

        self.connector = TerminalConnector()
        self.ai_model = AIModel()
        self.strategy = Strategy()
        self.db = DBClient()
        self.risk_manager = None
        self.current_day = 1
        self.virtual_equity = config.INITIAL_CAPITAL

    def log(self, message):
        if not os.path.exists(config.LOG_DIR): os.makedirs(config.LOG_DIR)
        log_file = os.path.join(config.LOG_DIR, "engine.log")
        ts = datetime.now(timezone.utc).strftime("%H:%M:%S")
        with open(log_file, "a") as f: f.write(f"[{ts}] {message}\n")
        print(f"[{ts}] {message}")

    def run(self):
        self.log("--- SINGULARITY ACTIVE: THE MONEY MACHINE ---")

        # 1. State Recovery
        latest = self.db.get_latest_state()
        if latest:
            self.current_day = latest.get("day_count", 1)
            self.virtual_equity = config.INITIAL_CAPITAL + self.db.get_total_realized_profit()
            self.log(f"STATE RESTORED: Day {self.current_day} | Virtual Equity: ${self.virtual_equity:.2f}")

        # 2. Connection
        if not self.connector.connect():
            self.log("MT5 CONNECTION FAILURE. ABORTING.")
            return

        try:
            account = self.connector.get_account_info()
            if not account: return

            self.risk_manager = RiskManagement(account, self.virtual_equity)

            # 3. Circuit Breaker
            initial_daily = latest.get("virtual_equity", self.virtual_equity) if latest else self.virtual_equity
            if self.risk_manager.check_circuit_breaker(initial_daily):
                self.log("DAILY DRAWDOWN LIMIT HIT. OPERATION HALTED.")
                return

            # 4. Management (No-Loss Logic)
            self.manage_trades()

            # 5. Execution Loop
            for sym in config.SYMBOLS:
                self.process_symbol(sym)

            # 6. State Snapshot
            self.snapshot(account)

        except Exception as e:
            self.log(f"CRITICAL SYSTEM ERROR: {e}")
        finally:
            self.connector.disconnect()
            self.log("--- CYCLE COMPLETE ---")

    def manage_trades(self):
        positions = self.connector.get_open_positions()
        for p in positions:
            # $0.05 Safety Switch: Move to Breakeven
            if p["profit"] > 0.05:
                self.log(f"SAFETY SWITCH: Locking BE for {p['symbol']}")
                self.connector.modify_sl(p["ticket"], p["price_open"], p["tp"])

    def process_symbol(self, symbol):
        df = self.connector.get_candles(symbol, config.DEFAULT_TIMEFRAME)
        if df is None or df.empty: return

        df = self.strategy.calculate_indicators(df)

        # ML Prediction
        if not os.path.exists(self.ai_model.model_path): self.ai_model.train(df)
        bull, bear = self.ai_model.predict(df)

        signal, confidence = self.strategy.generate_signal(df, bull, bear)
        self.log(f"SCAN: {symbol} | Signal: {signal} (C: {confidence})")

        # Stealth Execution & Filters
        if signal in ["BUY", "SELL"]:
            # ONE Position Only Global Filter for Phase 1
            if len(self.connector.get_open_positions()) >= config.MAX_OPEN_POSITIONS:
                return

            # Stealth Delay: 30-290s
            delay = random.randint(30, 290)
            self.log(f"STEALTH MODE: Waiting {delay}s before execution...")
            time.sleep(delay)

            lot = self.risk_manager.calculate_lot_size(self.current_day)
            entry = df.iloc[-1]['close']
            sl, tp = self.risk_manager.get_levels(signal, entry, df.iloc[-1]['ATR'])

            self.log(f"EXECUTING {signal} {symbol} | {lot} lots @ {entry}")
            res = self.connector.execute_order(symbol, signal, lot, sl, tp)
            if res:
                self.db.log_trade({
                    "symbol": symbol, "side": signal, "profit_loss": 0.0,
                    "status": "OPEN", "order_id": res.order, "confidence": confidence
                })

    def snapshot(self, account):
        # Update realized profit from history (Reconciliation)
        # Simplified: Virtual equity = Initial + Sum(DB trades)
        realized = self.db.get_total_realized_profit()
        self.virtual_equity = config.INITIAL_CAPITAL + realized

        # Check sequence progression
        for i, target in enumerate(config.TARGET_MULTIPLIER_SEQUENCE):
             if self.virtual_equity >= target:
                  self.current_day = i + 2

        self.db.save_state({
            "day_count": self.current_day,
            "virtual_equity": self.virtual_equity,
            "broker_balance": account["balance"]
        })

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
