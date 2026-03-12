import config
from terminal_connector import TerminalConnector
from ai_model import AIModel
from risk_management import RiskManagement
from strategy import Strategy
from db_client import DBClient
from data_engine import DataEngine
from genetic_optimizer import GeneticOptimizer
import time
import os
import random
import pandas as pd
from datetime import datetime, timezone

class AutonomousTradingMachine:
    def __init__(self):
        for d in ["logs", "trades", "signals", "data", "models"]:
            os.makedirs(os.path.join(config.BASE_DIR, d), exist_ok=True)

        self.db = DBClient()
        self.connector = TerminalConnector()
        self.ai_model = AIModel(db_client=self.db)
        self.data_engine = DataEngine(self.connector)
        self.strategy = Strategy()
        self.best_params = None
        self.risk_manager = None
        self.current_day = 1
        self.virtual_equity = config.INITIAL_CAPITAL

    def log(self, message, category="machine"):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(config.LOG_DIR, f"{category}.log")
        with open(log_file, "a") as f:
            f.write(f"[{ts}] {message}\n")
        print(f"[{category}] {message}")

    def run_cycle(self):
        self.log("--- STARTING AUTONOMOUS RESEARCH & TRADE CYCLE ---")

        # 1. State Recovery
        latest = self.db.get_latest_state()
        if latest:
            self.current_day = latest.get("day_count", 1)
            self.virtual_equity = config.INITIAL_CAPITAL + self.db.get_total_realized_profit()
            self.best_params = latest.get("best_params")
            self.log(f"STATE: Day {self.current_day} | Virtual Equity: ${self.virtual_equity:.2f}")

        # 2. Connect to MT5
        if not self.connector.connect():
            self.log("MT5 CONNECTION FAILURE.")
            return

        try:
            account = self.connector.get_account_info()
            if not account: return

            # 3. Data Acquisition
            market_data = self.data_engine.get_all_data()
            if not market_data:
                self.log("No market data available. Skipping optimization.")
                return

            # 4. AI Training (Full Data)
            for sym, df in market_data.items():
                self.ai_model.train(df)

            # 5. Genetic Optimization (Evolve Strategy)
            optimizer = GeneticOptimizer(market_data, self.ai_model)
            self.best_params = optimizer.evolve()
            self.log(f"EVOLVED PARAMS: {self.best_params}")

            # 6. Trade Execution Logic
            self.reconcile_trades()
            self.virtual_equity = config.INITIAL_CAPITAL + self.db.get_total_realized_profit()
            self.risk_manager = RiskManagement(account, self.virtual_equity)

            # 7. Management Loop (Break-even switch)
            self.manage_active_positions()

            # 8. Stealth Entry Execution
            # CIRCUIT BREAKER Check
            daily_start = latest.get("daily_start_equity", self.virtual_equity) if latest else self.virtual_equity
            if self.risk_manager.check_circuit_breaker(daily_start):
                self.log("CIRCUIT BREAKER ACTIVE: Halting new trades.")
            else:
                self.execute_trades(market_data)

            # 9. Persistence
            self.snapshot(account)

        except Exception as e:
            self.log(f"MACHINE ERROR: {e}")
        finally:
            self.connector.disconnect()
            self.log("--- CYCLE COMPLETE. ---")

    def manage_active_positions(self):
        positions = self.connector.get_open_positions()
        for p in positions:
            # SECTION 9: Move SL to break-even at $0.05 profit
            if p['profit'] >= 0.05 and p['sl'] != p['price_open']:
                self.log(f"BREAK-EVEN TRIGGER: Modifying {p['symbol']} SL to {p['price_open']}", category="trades")
                self.connector.modify_sl(p['ticket'], p['price_open'], p['tp'])

    def execute_trades(self, market_data):
        positions = self.connector.get_open_positions()

        for symbol, df in market_data.items():
            if any(p['symbol'] == symbol for p in positions): continue
            if len(positions) >= config.MAX_OPEN_POSITIONS: break

            df_with_ind = self.strategy.calculate_indicators(df)
            bull, bear = self.ai_model.predict(df_with_ind)

            signal = "WAIT"
            if bull > self.best_params['ai_threshold']: signal = "BUY"
            elif bear > self.best_params['ai_threshold']: signal = "SELL"

            if signal in ["BUY", "SELL"]:
                # STEALTH DELAY (30-290s)
                delay = random.randint(30, 290)
                self.log(f"STEALTH ENTRY: Waiting {delay}s for {symbol}...", category="trades")
                time.sleep(delay)

                lot = self.risk_manager.calculate_lot_size(self.current_day)
                lot = round(lot * 2, 2)

                entry = df.iloc[-1]['close']
                sl, tp = self.risk_manager.get_levels(signal, entry, df_with_ind.iloc[-1]['ATR'])

                self.log(f"TRADE EXECUTION: {signal} {symbol} (Prob: {max(bull, bear):.2f})", category="trades")
                res = self.connector.execute_order(symbol, signal, lot, sl, tp)
                if res:
                    self.db.log_trade({
                        "symbol": symbol, "side": signal, "profit_loss": 0.0,
                        "status": "OPEN", "order_id": res.order, "params": self.best_params
                    })

    def reconcile_trades(self):
        open_trades = self.db.get_open_logged_trades()
        if not open_trades: return
        closed_deals = self.connector.get_closed_deals()
        exit_deals = {str(d["order"]): d for d in closed_deals if d["entry"] == 1}
        for trade in open_trades:
            order_id = str(trade.get("order_id"))
            if order_id in exit_deals:
                deal = exit_deals[order_id]
                self.db.update_trade(order_id, {
                    "status": "CLOSED", "profit_loss": float(deal.get("profit", 0)),
                    "exit_time": time.time()
                })

    def snapshot(self, account):
        realized = self.db.get_total_realized_profit()
        self.virtual_equity = config.INITIAL_CAPITAL + realized
        if self.virtual_equity > config.COMPOUNDING_THRESHOLD:
            self.current_day += 1

        self.db.save_state({
            "day_count": self.current_day,
            "virtual_equity": self.virtual_equity,
            "best_params": self.best_params,
            "broker_balance": account["balance"],
            "daily_start_equity": self.virtual_equity
        })

if __name__ == "__main__":
    machine = AutonomousTradingMachine()
    machine.run_cycle()
