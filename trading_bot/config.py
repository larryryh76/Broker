import os
import logging
from dotenv import load_dotenv

load_dotenv()

# Logger configuration
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("TheMoneyMachine")

# Broker Credentials
MT5_LOGIN = int(os.getenv("MT5_LOGIN", "0"))
MT5_PASSWORD = os.getenv("MT5_PASSWORD", "")
MT5_SERVER = os.getenv("MT5_SERVER", "")

# Bot Settings
SYMBOLS = ["EURUSD", "GBPUSD", "USDJPY", "XAUUSD"]
TIMEFRAMES = ["M5", "M15", "H1"]
DEFAULT_TIMEFRAME = "M5"

# Optimization Settings
POPULATION_SIZE = 50
GENERATIONS = 5
MUTATION_RATE = 0.1
ELITE_PERCENT = 0.1

# Optimization: Max 3 simultaneous positions as per brief
MAX_OPEN_POSITIONS = 3
MAX_TRADES_PER_SYMBOL = 1

# Strategy Parameters (Defaults)
RSI_PERIOD = 14
RSI_OVERBOUGHT = 70
RSI_OVERSOLD = 30
SMA_FAST = 20
SMA_SLOW = 50

# Risk Management
INITIAL_CAPITAL = 5.0
DAILY_DRAWDOWN_LIMIT = 0.20  # 20% of balance (Aggressive)
COMPOUNDING_THRESHOLD = 50.0
TARGET_MULTIPLIER_SEQUENCE = [50, 250, 1500, 10500, 84000, 756000, 7560000]
RISK_PER_TRADE = 0.20 # 20% risk per trade as requested

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")
MODEL_DIR = os.path.join(BASE_DIR, "models")
DATA_DIR = os.path.join(BASE_DIR, "data")
# Unified repository-local path for MT5 terminal (STEP 2)
TERMINAL_DIR = os.path.join(os.path.dirname(BASE_DIR), "mt5_terminal")
