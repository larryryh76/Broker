# THE MONEY MACHINE - Architecture Documentation (Direct MT5 Edition)

## Overview
THE MONEY MACHINE is a production-ready trading bot designed to execute on a GitHub Actions schedule. It uses a multi-indicator strategy to trade Gold (XAUUSD), GBP/JPY (GBPJPY), and Bitcoin (BTCUSD) via the Exness broker using the official MetaTrader 5 Python library.

## Core Components

### 1. MT5 Client (`mt5_client.py`)
- Interfaces directly with the MetaTrader 5 terminal using the `MetaTrader5` Python library.
- Handles market data acquisition, account status, and trade execution.
- **Note**: This library requires a Windows environment and an active MT5 terminal.

### 2. Strategy Engine (`strategy.py`)
- **Technical Indicators**: RSI (7), Fast SMA (20), Slow SMA (50), and Bollinger Bands.
- **Signal Generation**: Hyper-aggressive RSI/BB alignment + **Market Mistake Filter** (instant reversal if price deviates >100 points from MA).
- **Market Structure Filter**: REQUIRED proximity to Daily High/Low or Pivot Points (P, S1, R1) before entry.
- **Trend Alignment Filter**: No BUY if H1 trend is DOWN; no SELL if H1 trend is UP (Trend defined by H1 SMA 20).
- **Volatility Filter**: Only executes if spread < 10% of Daily ATR.
- **Risk Management**: 1:3 Risk-to-Reward ratio.
- **Position Sizing**: Dynamic micro-lot sizing ($5 -> 0.05 lots) with **Gold Overrides** (0.10 - 0.50 lots) for Phase 1 compounding.
- **Safety Buffer**: Hard Reset triggers if Virtual Equity drops below $3.50, re-seeding the bot and ignoring past historical/manual data via Magic Number filtering.
- **Recursive Learning**: Scales risk based on real-time win rates.

### 3. Database Client (`db_client.py`)
- Uses MongoDB Atlas for persistence.
- Tracks trade history and daily performance snapshots.

### 4. Execution Layer (`executor.py`)
- Manages the execution cycle: circuit breaker check -> analysis -> immediate execution -> trade management.
- **Maximum ONE Open Position**: Strictly forbidden from opening a second trade globally if one is already open, preventing "stacking losses".
- **Entry Cooling**: Implements a 5-second sleep after each execution to prevent redundant entries.
- **Direct Execution**: Bypasses delays and handshakes to maximize efficiency within the 5-minute GitHub Actions window.
- **Active Management**: Implements the **$0.05 Safety Switch** (moves SL to +$0.01 profit once +$0.05 reached) and aggressive trailing stops (10-point trail).
- **Duplicate Prevention**: Skips signals if a position is already open for that symbol.

### 5. Deployment (`.github/workflows/trading-bot-schedule.yml`)
- Runs on **`windows-latest`** GitHub Actions runner to support the MT5 library.
- Executes every 5 minutes via cron.

## Setup Instructions

### Prerequisites
1. **Exness Account**: Obtain your Login and Server details from the Exness Personal Area.
2. **MongoDB Atlas**: A cluster with a connection string.
3. **MetaTrader 5**: Ensure the terminal is installed if running locally on Windows.

### GitHub Secrets Configuration
Store the following in your GitHub repository secrets:
- `MT5_LOGIN`: Your Exness account number.
- `MT5_PASSWORD`: Your trading password.
- `MT5_SERVER`: Your account's server (e.g., Exness-MT5Trial9).
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
   - Places aggressive micro-lot trade (0.05 - 0.50) with SL/TP immediately.
6. Monitors open positions:
   - Triggers $0.05 Safety Switch at target profit.
   - Activates 10-point Trailing Stop.
7. Logs activity to MongoDB and updates learning state.
