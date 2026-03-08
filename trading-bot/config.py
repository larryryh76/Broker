import os
from dotenv import load_dotenv

load_dotenv()

# Broker Credentials
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")

# Bot Settings
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
TIMEFRAMES = ["M5", "M15", "H1"]
DEFAULT_TIMEFRAME = "M5"

# Phase 1 Optimization: Strict one-position limit
MAX_OPEN_POSITIONS = 1
MAX_TRADES_PER_SYMBOL = 1

# Strategy Parameters
RSI_PERIOD = 7  # Faster RSI for small accounts
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
SMA_FAST = 20
SMA_SLOW = 50

# Risk Management
INITIAL_CAPITAL = 5.0
DAILY_DRAWDOWN_LIMIT = 0.05  # 5% of balance
COMPOUNDING_THRESHOLD = 50.0
TARGET_MULTIPLIER_SEQUENCE = [50, 250, 1500, 10500, 84000, 756000, 7560000] # 10x scaling after initial flip

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
TERMINAL_DIR = os.path.join(os.path.dirname(BASE_DIR), "mt5_terminal")
