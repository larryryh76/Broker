import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

# OANDA Configuration
OANDA_TOKEN = os.getenv("OANDA_TOKEN")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID")
# Default to practice API, can be overridden by environment variable
OANDA_URL = os.getenv("OANDA_URL", "https://api-fxpractice.oanda.com/v3")

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "the_money_machine")

# Trading Configuration
# OANDA instrument format is usually CURRENCY_CURRENCY or COMMODITY_CURRENCY
INSTRUMENTS = ["XAU_USD", "GBP_JPY", "BTC_USD"]
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
    if not OANDA_TOKEN:
        missing.append("OANDA_TOKEN")
    if not OANDA_ACCOUNT_ID:
        missing.append("OANDA_ACCOUNT_ID")
    if not MONGODB_URI:
        missing.append("MONGODB_URI")

    if missing:
        logger.error(f"Missing environment variables: {', '.join(missing)}")
        return False
    return True
