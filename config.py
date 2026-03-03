import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

# MetaTrader 5 Configuration
MT5_LOGIN = int(os.getenv("MT5_LOGIN", 0))
MT5_PASSWORD = os.getenv("MT5_PASSWORD")
MT5_SERVER = os.getenv("MT5_SERVER")

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "the_money_machine")

# Trading Configuration
# BTC/ETH pruned to focus margin on Forex and Gold for Phase 1 Compounding
INSTRUMENTS = ["XAUUSD", "GBPJPY", "EURUSD"]
RISK_REWARD_RATIO = 3
DAILY_DRAWDOWN_LIMIT = 0.05
MIN_CONFIDENCE = 0.70

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("MoneyMachine")

def validate_config():
    missing = []
    if not MT5_LOGIN:
        missing.append("MT5_LOGIN")
    if not MT5_PASSWORD:
        missing.append("MT5_PASSWORD")
    if not MT5_SERVER:
        missing.append("MT5_SERVER")
    if not MONGODB_URI:
        missing.append("MONGODB_URI")

    if missing:
        logger.error(f"CONFIGURATION ERROR: The following required environment variables are missing: {', '.join(missing)}")
        logger.error("Please ensure these are set in your GitHub Secrets or .env file.")
        return False

    logger.info("Configuration validated successfully.")
    return True
