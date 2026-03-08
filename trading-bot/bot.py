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
            self.log(f"DB Warning: {e}")

        # 2. Connection
        if not self.connector.connect():
            self.log("MT5 CONNECTION FAILURE. ABORTING.")
            return

        try:
            account = self.connector.get_account_info()
            if not account: return

            # Initial Reconciliation: Fetch closed deals from MT5 and update DB
            self.reconcile_trades()

            # Re-calculate equity after reconciliation
            self.virtual_equity = config.INITIAL_CAPITAL + self.db.get_total_realized_profit()

            # HARD RESET CHECK: If equity falls below $0.50 (90% loss)
            if self.virtual_equity < 0.50:
                self.log("VIRTUAL ACCOUNT BLOWN - PERFORMING HARD RESET.")
                self.db.clear_all_trades()
                self.db.clear_learning_state()
                self.virtual_equity = config.INITIAL_CAPITAL
                self.current_day = 1

            self.risk_manager = RiskManagement(account, self.virtual_equity)

            # 3. Circuit Breaker
            initial_daily = latest.get("virtual_equity", self.virtual_equity) if latest else self.virtual_equity
            if self.risk_manager.check_circuit_breaker(initial_daily):
                self.log("DAILY DRAWDOWN LIMIT HIT. OPERATION HALTED.")
                return

            # 4. Management & Reversal Check
            self.manage_trades()

            # 5. Opportunity Scan
            for sym in config.SYMBOLS:
                self.process_symbol(sym)

            # 6. Cycle Summary
            self.snapshot(account)

        except Exception as e:
            self.log(f"CRITICAL ENGINE ERROR: {e}")
            import traceback
            self.log(traceback.format_exc())
        finally:
            self.connector.disconnect()
            self.log("--- CYCLE COMPLETE ---")

    def reconcile_trades(self):
        self.log("Reconciling trades with MT5 history...")
        open_logged_trades = self.db.get_open_logged_trades()
        if not open_logged_trades:
            return

        closed_deals = self.connector.get_closed_deals()
        # Deals with entry=DEAL_ENTRY_OUT (1) are exit deals
        exit_deals = {str(d["order"]): d for d in closed_deals if d["entry"] == 1}

        for trade in open_logged_trades:
            order_id = str(trade.get("order_id"))
            if order_id in exit_deals:
                deal = exit_deals[order_id]
                profit = float(deal.get("profit", 0))
                self.log(f"Reconciled closed trade {order_id}: Profit ${profit:.2f}")
                self.db.update_trade(order_id, {
                    "status": "CLOSED",
                    "profit_loss": profit,
                    "exit_price": deal.get("price"),
                    "exit_time": time.time()
                })

    def manage_trades(self):
        positions = self.connector.get_open_positions()
        for p in positions:
            symbol = p["symbol"]
            ticket = p["ticket"]
            profit = p["profit"]
            p_type = p["type"]

            # $0.05 Safety Switch
            if profit > 0.05:
                self.log(f"SAFETY SWITCH: Locking BE for {symbol}")
                self.connector.modify_sl(ticket, p["price_open"], p["tp"])

            # Signal Reversal Check
            df = self.connector.get_candles(symbol, config.DEFAULT_TIMEFRAME)
            if df is not None and not df.empty:
                df = self.strategy.calculate_indicators(df)
                bull, bear = self.ai_model.predict(df)
                signal, _ = self.strategy.generate_signal(df, bull, bear)

                if (p_type == 0 and signal == "SELL") or (p_type == 1 and signal == "BUY"):
                    self.log(f"REVERSAL DETECTED: Closing {symbol} due to {signal} signal.")
                    self.connector.close_position(ticket)

    def process_symbol(self, symbol):
        df = self.connector.get_candles(symbol, config.DEFAULT_TIMEFRAME)
        if df is None or df.empty: return

        df = self.strategy.calculate_indicators(df)
        bull, bear = self.ai_model.predict(df)
        signal, confidence = self.strategy.generate_signal(df, bull, bear)

        self.log(f"SCAN: {symbol} | Signal: {signal} (C: {confidence:.1f})")

        if signal in ["BUY", "SELL"]:
            current_pos = self.connector.get_open_positions()
            if len(current_pos) >= config.MAX_OPEN_POSITIONS:
                return

            # Stealth window
            delay = random.randint(30, 290)
            self.log(f"STEALTH: Executing in {delay}s...")
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
        realized = self.db.get_total_realized_profit()
        self.virtual_equity = config.INITIAL_CAPITAL + realized

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
