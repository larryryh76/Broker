# THE MONEY MACHINE - Architecture Documentation (Direct MT5 Edition)

## Overview
THE MONEY MACHINE is an ultra-intelligent, autonomous trading system. It operates using a **Virtual Sub-Capital Model**, isolating a fixed $5.00 starting capital from the broker's main balance. All risk, sizing, and objectives are calculated exclusively from this virtual sub-account.

## Core Components

### 1. MT5 Client (`mt5_client.py`)
- Interfaces directly with the MetaTrader 5 terminal using the `MetaTrader5` Python library.
- Handles market data acquisition, account status, and trade execution.
- **Note**: This library requires a Windows environment and an active MT5 terminal. Operates in a pure headless mode without visualization overhead.

### 2. Strategy Engine (`strategy.py`)
- **Technical Indicators**: RSI (7), Fast SMA (20), Slow SMA (50), and Bollinger Bands.
- **Signal Generation**: Hyper-aggressive RSI/BB alignment + **Market Mistake Filter** (instant reversal if price deviates >100 points from MA).
- **Market Structure Filter**: REQUIRED proximity to Daily High/Low or Pivot Points (P, S1, R1) before entry.
- **Trend Alignment Filter**: No BUY if H1 trend is DOWN; no SELL if H1 trend is UP (Trend defined by H1 SMA 20).
- **Volatility Filter**: Only executes if spread < 10% of Daily ATR.
- **Risk Management**: 1:3 Risk-to-Reward ratio.
- **Position Sizing**: Dynamic micro-lot sizing calculated EXCLUSIVELY from the $5.00 virtual sub-capital + realized profit.
- **Safety Buffer**: Hard Reset triggers if Virtual Equity drops below $3.50, re-seeding the bot and ignoring past historical/manual data via Magic Number (123456) filtering.
- **Virtual Sub-Capital Model**: Broker balance is treated as an untouched reserve. All risk and sizing is derived EXCLUSIVELY from an isolated $5.00 base.
- **Profit Scaling**: Progressive multiplication logic ($50 -> x5 -> x6 -> x7 -> x8 -> x9 -> x10) based on realized virtual growth.
- **Aggression Escalation**: Multiplier increases and entry thresholds relax incrementally for each cycle without execution to ensure daily targets are met.
- **Loss Intelligence**: Predictive parameters adapt immediately after losses to prevent recurring failures.
- **Recursive Learning**: Scales risk based on real-time win rates.

### 3. Database Client (`db_client.py`)
- Uses MongoDB Atlas for persistence.
- Tracks trade history and daily performance snapshots.

### 4. Execution Layer (`executor.py`)
- Manages the execution cycle: circuit breaker check -> analysis -> immediate execution -> trade management.
- **Maximum ONE Open Position**: Strictly forbidden from opening a second trade globally if one is already open, preventing "stacking losses".
- **Intelligence Filter**: Implements a 10-second cooldown between consecutive Stop Loss modifications to prevent system errors.
- **Entry Cooling**: Implements a 5-second sleep after each execution to prevent redundant entries.
- **Direct Execution**: Bypasses delays and handshakes to maximize efficiency within the 5-minute GitHub Actions window.
- **Active Management**: Implements the **$0.05 Safety Switch** (moves SL to +$0.01 profit once +$0.05 reached) and aggressive trailing stops (10-point trail).
- **Duplicate Prevention**: Skips signals if a position is already open for that symbol.

### 5. Deployment (`.github/workflows/trading-bot-schedule.yml`)
- Runs on **`windows-latest`** GitHub Actions runner to support the MT5 library.
- Executes every 5 minutes via cron.

## Setup Instructions

### Prerequisites
1. **Trading Account**: Obtain your MT5 Login and Server details from your broker (e.g., FBS).
2. **MongoDB Atlas**: A cluster with a connection string.
3. **MetaTrader 5**: Ensure the terminal is installed if running locally on Windows.

### GitHub Secrets Configuration
Store the following in your GitHub repository secrets:
- `MT5_LOGIN`: Your MT5 account number.
- `MT5_PASSWORD`: Your trading password.
- `MT5_SERVER`: Your account's server (e.g., FBS-Real).
- `MONGODB_URI`: Your MongoDB Atlas connection string.

### Direct File Setup (GitHub Actions)
To avoid installation issues on GitHub runners:
1. Copy the contents of your MetaTrader 5 installation from your computer.
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
