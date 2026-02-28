import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file for local development
load_dotenv()

# MetaApi / Exness Configuration
META_API_TOKEN = os.getenv("META_API_TOKEN")
META_API_ACCOUNT_ID = os.getenv("META_API_ACCOUNT_ID")

# MongoDB Configuration
MONGODB_URI = os.getenv("MONGODB_URI")
DB_NAME = os.getenv("DB_NAME", "the_money_machine")

# Trading Configuration
# Exness instrument names (standard accounts usually no suffix, pro accounts might have 'm' or other)
INSTRUMENTS = ["XAUUSD", "GBPJPY", "BTCUSD"]
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
    if not META_API_TOKEN:
        missing.append("META_API_TOKEN")
    if not META_API_ACCOUNT_ID:
        missing.append("META_API_ACCOUNT_ID")
    if not MONGODB_URI:
        missing.append("MONGODB_URI")

    if missing:
        logger.error(f"CONFIGURATION ERROR: The following required environment variables are missing: {', '.join(missing)}")
        logger.error("Please ensure these are set in your GitHub Secrets or .env file.")
        return False

    logger.info("Configuration validated successfully.")
    return True
