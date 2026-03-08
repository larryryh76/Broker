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
        # 1. Environment Prep: Inject configuration before any connection attempts
        print("Initializing headless environment configuration...")
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

    def run(self):
        self.log("--- SINGULARITY ACTIVE: THE MONEY MACHINE ---")

        # 1. State Recovery
        try:
            latest = self.db.get_latest_state()
            if latest:
                self.current_day = latest.get("day_count", 1)
                self.virtual_equity = config.INITIAL_CAPITAL + self.db.get_total_realized_profit()
                self.log(f"STATE RESTORED: Day {self.current_day} | Virtual Equity: ${self.virtual_equity:.2f}")
        except Exception as e:
            self.log(f"DB Warning: Could not recover state: {e}")

        # 2. Connection Phase (Includes terminal startup and retries)
        if not self.connector.connect():
            self.log("MT5 CONNECTION FAILURE. ABORTING EXECUTION.")
            return

        try:
            account = self.connector.get_account_info()
            if not account:
                self.log("Could not retrieve account info. Aborting.")
                return

            self.risk_manager = RiskManagement(account, self.virtual_equity)
            self.log(f"ACCOUNT INFO: Balance ${account['balance']} | Leverage {account['leverage']}")

            # 3. Circuit Breaker Evaluation
            initial_daily = latest.get("virtual_equity", self.virtual_equity) if latest else self.virtual_equity
            if self.risk_manager.check_circuit_breaker(initial_daily):
                self.log("DAILY DRAWDOWN LIMIT HIT. OPERATION SUSPENDED.")
                return

            # 4. Active Trade Management
            self.manage_trades()

            # 5. Opportunity Scan & Order Execution
            for sym in config.SYMBOLS:
                self.process_symbol(sym)

            # 6. Cycle Summary & Persistence
            self.snapshot(account)

        except Exception as e:
            self.log(f"CRITICAL ENGINE ERROR: {e}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            self.connector.disconnect()
            self.log("--- CYCLE COMPLETE ---")

    def manage_trades(self):
        positions = self.connector.get_open_positions()
        self.log(f"MANAGE: Checking {len(positions)} open positions.")
        for p in positions:
            symbol = p["symbol"]
            ticket = p["ticket"]
            profit = p["profit"]
            p_type = p["type"]

            # A. $0.05 Safety Switch (Move SL to break-even)
            if profit > 0.05:
                self.log(f"SAFETY SWITCH: Locking profit for {symbol} ({ticket})")
                self.connector.modify_sl(ticket, p["price_open"], p["tp"])

            # B. Strategy Reversal Check
            df = self.connector.get_candles(symbol, config.DEFAULT_TIMEFRAME)
            if df is not None and not df.empty:
                df = self.strategy.calculate_indicators(df)
                bull, bear = self.ai_model.predict(df)
                signal, _ = self.strategy.generate_signal(df, bull, bear)

                # Immediate exit on signal flip
                if (p_type == 0 and signal == "SELL") or (p_type == 1 and signal == "BUY"):
                    self.log(f"REVERSAL DETECTED: Closing {symbol} due to {signal} signal.")
                    self.connector.close_position(ticket)

    def process_symbol(self, symbol):
        df = self.connector.get_candles(symbol, config.DEFAULT_TIMEFRAME)
        if df is None or df.empty:
            self.log(f"DATA: No candles for {symbol}")
            return

        df = self.strategy.calculate_indicators(df)

        # Continuous Adaptation: Retrain model if not present (handled inside AIModel)
        bull, bear = self.ai_model.predict(df)

        signal, confidence = self.strategy.generate_signal(df, bull, bear)
        self.log(f"SCAN: {symbol} | Signal: {signal} | Conf: {confidence:.2f}")

        if signal in ["BUY", "SELL"]:
            # Risk/Constraint Verification
            current_pos = self.connector.get_open_positions()

            # Brief requirement: Max 3 simultaneous open positions
            if len(current_pos) >= config.MAX_OPEN_POSITIONS:
                self.log(f"SKIP: Global limit reached ({config.MAX_OPEN_POSITIONS})")
                return

            # Stealth Window Randomization
            delay = random.randint(30, 290)
            self.log(f"STEALTH: Executing in {delay}s...")
            time.sleep(delay)

            lot = self.risk_manager.calculate_lot_size(self.current_day)
            entry = df.iloc[-1]['close']
            sl, tp = self.risk_manager.get_levels(signal, entry, df.iloc[-1]['ATR'])

            self.log(f"ORDER: {signal} {symbol} | {lot} lots @ {entry}")
            res = self.connector.execute_order(symbol, signal, lot, sl, tp)
            if res:
                self.db.log_trade({
                    "symbol": symbol, "side": signal, "profit_loss": 0.0,
                    "status": "OPEN", "order_id": res.order, "confidence": confidence
                })

    def snapshot(self, account):
        realized = self.db.get_total_realized_profit()
        self.virtual_equity = config.INITIAL_CAPITAL + realized

        # Update geometric compounding progression
        for i, target in enumerate(config.TARGET_MULTIPLIER_SEQUENCE):
             if self.virtual_equity >= target:
                  self.current_day = i + 2

        self.log(f"SNAPSHOT: Equity ${self.virtual_equity:.2f} | Day {self.current_day}")
        self.db.save_state({
            "day_count": self.current_day,
            "virtual_equity": self.virtual_equity,
            "broker_balance": account["balance"]
        })

if __name__ == "__main__":
    bot = TradingBot()
    bot.run()
