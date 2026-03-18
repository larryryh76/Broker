import config
from trading_bot.terminal_connector import TerminalConnector
from trading_bot.db_client import DBClient
from trading_bot.data_engine import DataEngine
from trading_bot.strategy import Strategy
from trading_bot.ai_model import AIModel
from trading_bot.risk_management import RiskManagement
import os
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

    def log(self, message, category="machine"):
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        log_file = os.path.join(config.LOG_DIR, f"{category}.log")
        with open(log_file, "a") as f:
            f.write(f"[{ts}] {message}\n")
        print(f"[{category}] {message}")

    def reconcile_trades(self):
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
            self.log("CRITICAL: Bridge failed. Terminating.")
            return

        try:
            realized_profit = self.reconcile_trades()
            virtual_equity = config.INITIAL_CAPITAL + realized_profit
            account = self.connector.get_account_info()
            if not account: return

            risk_manager = RiskManagement(account, virtual_equity)
            state = self.db.get_latest_state()
            daily_start_equity = state.get("daily_start_equity", virtual_equity) if state else virtual_equity

            now = datetime.now(timezone.utc)
            if state and "snapshot" in state and "timestamp" in state["snapshot"]:
                last_ts = datetime.fromisoformat(state["snapshot"]["timestamp"])
                if last_ts.date() < now.date(): daily_start_equity = virtual_equity

            if risk_manager.check_circuit_breaker(daily_start_equity):
                self.log("CIRCUIT BREAKER: Drawdown limit reached.")
                return

            self.db.save_state({"snapshot": {"timestamp": now.isoformat()}, "daily_start_equity": daily_start_equity})

            open_positions = self.connector.get_open_positions()
            for pos in open_positions:
                symbol = pos['symbol']
                df = self.data_engine.download_data(symbol, config.DEFAULT_TIMEFRAME)
                if df is not None:
                    df = self.strategy.calculate_indicators(df)
                    bull_prob, bear_prob = self.ai_model.predict(df)
                    signal, _ = self.strategy.generate_signal(df, bull_prob, bear_prob)

                    if (pos['type'] == 0 and signal == "SELL") or (pos['type'] == 1 and signal == "BUY"):
                        self.connector.close_position(pos['ticket'])
                    elif pos['profit'] >= 0.05:
                        self.connector.modify_sl(pos['ticket'], pos['price_open'], pos['tp'])

            if len(open_positions) < config.MAX_OPEN_POSITIONS:
                for symbol in config.SYMBOLS:
                    if any(p['symbol'] == symbol for p in open_positions): continue
                    df = self.data_engine.download_data(symbol, config.DEFAULT_TIMEFRAME)
                    if df is None: continue
                    df = self.strategy.calculate_indicators(df)
                    bull_prob, bear_prob = self.ai_model.predict(df)
                    signal, confidence = self.strategy.generate_signal(df, bull_prob, bear_prob)

                    if signal in ["BUY", "SELL"]:
                        lot = risk_manager.calculate_lot_size(1)
                        mapped_symbol = self.connector.map_symbol(symbol)
                        tick = self.connector.mt5.symbol_info_tick(mapped_symbol)
                        if tick is None: continue
                        current_price = tick.ask if signal == "BUY" else tick.bid
                        sl, tp = risk_manager.get_levels(signal, current_price, df.iloc[-1]['ATR'])
                        res = self.connector.execute_order(symbol, signal, lot, sl, tp)
                        if res and res.retcode == self.connector.mt5.TRADE_RETCODE_DONE:
                            self.db.log_trade({"order_id": res.order, "symbol": symbol, "status": "OPEN"})
                    if len(self.connector.get_open_positions()) >= config.MAX_OPEN_POSITIONS: break
        finally:
            if self.connector and hasattr(self.connector, 'disconnect'):
                self.connector.disconnect()

if __name__ == "__main__":
    machine = TradingMachine()
    machine.run_cycle()
