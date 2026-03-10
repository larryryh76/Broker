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
        # Ensure directories for artifacts exist
        for d in ["logs", "trades", "signals"]:
            os.makedirs(os.path.join(config.BASE_DIR, d), exist_ok=True)

        inject_headless_config()
        self.db = DBClient()
        self.connector = TerminalConnector()
        self.ai_model = AIModel(db_client=self.db)
        self.strategy = Strategy()
        self.risk_manager = None
        self.current_day = 1
        self.virtual_equity = config.INITIAL_CAPITAL

    def log(self, message, category="engine"):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(config.LOG_DIR, f"{category}.log")
        with open(log_file, "a") as f:
            f.write(f"[{ts}] {message}\n")
        print(f"[{category}] {message}")

    def run_single_cycle(self):
        # SECTION 6 — Single Trading Cycle Structure
        self.log("--- STARTING SINGLE TRADING CYCLE ---")

        # STEALTH EXECUTION: Randomize entry within the window (30-290s)
        delay = random.randint(30, 290)
        self.log(f"Stealth Delay Activated: Waiting {delay} seconds before execution...")
        time.sleep(delay)

        # 1. State Recovery
        latest = self.db.get_latest_state()
        if latest:
            self.current_day = latest.get("day_count", 1)
            self.virtual_equity = config.INITIAL_CAPITAL + self.db.get_total_realized_profit()
            self.log(f"STATE: Day {self.current_day} | Virtual Equity: ${self.virtual_equity:.2f}")

        # 2. Connection (Handled in connector with retries)
        if not self.connector.connect():
            self.log("MT5 CONNECTION FAILURE. EXITING RUN.")
            return

        try:
            account = self.connector.get_account_info()
            if not account: return

            # Initial Reconciliation
            self.reconcile_trades()
            self.virtual_equity = config.INITIAL_CAPITAL + self.db.get_total_realized_profit()

            # Hard Reset Check
            if self.virtual_equity < 0.50:
                self.log("HARD RESET.")
                self.db.clear_all_trades()
                self.db.clear_learning_state()
                self.virtual_equity = config.INITIAL_CAPITAL
                self.current_day = 1

            self.risk_manager = RiskManagement(account, self.virtual_equity)

            # 3. Market Analysis & Signal Generation
            self.manage_trades()

            for sym in config.SYMBOLS:
                self.process_symbol(sym)

            # 4. Snapshot
            self.snapshot(account)

        except Exception as e:
            self.log(f"CYCLE ERROR: {e}")
        finally:
            # SECTION 7 — Safe Shutdown
            self.connector.disconnect()
            self.log("--- CYCLE COMPLETE. MT5 SHUTDOWN. ---")

    def reconcile_trades(self):
        open_logged_trades = self.db.get_open_logged_trades()
        if not open_logged_trades: return
        closed_deals = self.connector.get_closed_deals()
        exit_deals = {str(d["order"]): d for d in closed_deals if d["entry"] == 1}
        for trade in open_logged_trades:
            order_id = str(trade.get("order_id"))
            if order_id in exit_deals:
                deal = exit_deals[order_id]
                profit = float(deal.get("profit", 0))
                self.log(f"TRADE CLOSED: {order_id} | PL: ${profit:.2f}", category="trades")
                self.db.update_trade(order_id, {
                    "status": "CLOSED", "profit_loss": profit,
                    "exit_price": deal.get("price"), "exit_time": time.time()
                })

    def manage_trades(self):
        positions = self.connector.get_open_positions()
        for p in positions:
            symbol = p["symbol"]
            if p["profit"] > 0.05:
                self.connector.modify_sl(p["ticket"], p["price_open"], p["tp"])

            # Reversal logic
            df = self.connector.get_candles(symbol, config.DEFAULT_TIMEFRAME)
            if df is not None and not df.empty:
                df = self.strategy.calculate_indicators(df)
                bull, bear = self.ai_model.predict(df)
                signal, _ = self.strategy.generate_signal(df, bull, bear)
                if (p["type"] == 0 and signal == "SELL") or (p["type"] == 1 and signal == "BUY"):
                    self.log(f"REVERSAL: Closing {symbol}", category="trades")
                    self.connector.close_position(p["ticket"])

    def process_symbol(self, symbol):
        # Skip if market closed (SECTION 9)
        # Simplified: checking if we can get recent candles
        df = self.connector.get_candles(symbol, config.DEFAULT_TIMEFRAME, count=100)
        if df is None or df.empty:
            self.log(f"Market closed or no data for {symbol}. Skipping.")
            return

        df = self.strategy.calculate_indicators(df)
        if not self.ai_model.is_trained: self.ai_model.train(df)
        bull, bear = self.ai_model.predict(df)
        signal, confidence = self.strategy.generate_signal(df, bull, bear)

        if signal != "WAIT":
            self.log(f"SIGNAL: {symbol} {signal} (C: {confidence})", category="signals")

        if signal in ["BUY", "SELL"]:
            if len(self.connector.get_open_positions()) >= config.MAX_OPEN_POSITIONS: return

            lot = self.risk_manager.calculate_lot_size(self.current_day)
            entry = df.iloc[-1]['close']
            sl, tp = self.risk_manager.get_levels(signal, entry, df.iloc[-1]['ATR'])

            self.log(f"EXECUTION: {signal} {symbol} @ {entry}", category="trades")
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

if __name__ == "__main__":
    bot = TradingBot()
    bot.run_single_cycle()
