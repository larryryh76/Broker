# THE MONEY MACHINE - Architecture Documentation (Direct MT5 Edition)

## Overview
THE MONEY MACHINE is a production-ready trading bot designed to execute on a GitHub Actions schedule. It uses a multi-indicator strategy to trade Gold (XAUUSD), GBP/JPY (GBPJPY), and Bitcoin (BTCUSD) via the Exness broker using the official MetaTrader 5 Python library.

## Core Components

### 1. MT5 Client (`mt5_client.py`)
- Interfaces directly with the MetaTrader 5 terminal using the `MetaTrader5` Python library.
- Handles market data acquisition, account status, and trade execution.
- **Note**: This library requires a Windows environment and an active MT5 terminal.

### 2. Strategy Engine (`strategy.py`)
- **Technical Indicators**: RSI (14), Fast SMA (20), and Slow SMA (50).
- **Signal Generation**: Requires 2 out of 3 indicator alignment.
- **Risk Management**: 1:3 Risk-to-Reward ratio.
- **Position Sizing**: Dynamic micro-lot sizing (0.01 minimum) optimized for small accounts ($5+).
- **Recursive Learning**: Scales risk based on real-time win rates.

### 3. Database Client (`db_client.py`)
- Uses MongoDB Atlas for persistence.
- Tracks trade history and daily performance snapshots.

### 4. Execution Layer (`executor.py`)
- Manages the execution cycle: circuit breaker check -> analysis -> stealth delay -> order placement.
- **Duplicate Prevention**: Skips signals if a position is already open for that symbol.

### 5. Deployment (`.github/workflows/trading-bot-schedule.yml`)
- Runs on **`windows-latest`** GitHub Actions runner to support the MT5 library.
- Executes every 5 minutes via cron.

## Setup Instructions

### Prerequisites
1. **Exness Account**: Login: `298682494`, Server: `Exness-MT5Trial9`.
2. **MongoDB Atlas**: A cluster with a connection string.
3. **MetaTrader 5**: Ensure the terminal is installed if running locally on Windows.

### GitHub Secrets Configuration
Store the following in your GitHub repository secrets:
- `MT5_LOGIN`: `298682494`
- `MT5_PASSWORD`: `Iamolanrewaju1$`
- `MT5_SERVER`: `Exness-MT5Trial9`
- `MONGODB_URI`: Your MongoDB Atlas connection string.

### Direct File Setup (GitHub Actions)
To avoid installation issues on GitHub runners:
1. Copy the contents of `C:\Program Files\Exness MetaTrader 5` from your computer.
2. Upload them to a folder named `mt5_terminal` in the root of this repository.
3. Ensure `terminal64.exe` is inside that folder.

### Local Development (Windows Only)
1. Install dependencies: `pip install -r requirements.txt`.
2. Run MT5 Terminal and log in to your account.
3. Run the bot: `python main.py`.

## Workflow
1. GitHub Actions (Windows) triggers every 5 minutes.
2. Bot initializes MT5 using the executable in `./mt5_terminal/terminal64.exe`.
3. Bot checks for >5% Daily Drawdown (Circuit Breaker).
4. Bot analyzes markets for RSI/SMA alignment.
5. If signal found and no duplicate position exists:
   - Waits a random 30-290 seconds.
   - Places 0.01 micro-lot trade with SL/TP.
6. Logs activity to MongoDB and updates learning state.
