# THE MONEY MACHINE - Architecture Documentation (Exness Edition)

## Overview
THE MONEY MACHINE is a production-ready, serverless trading bot designed to execute on a GitHub Actions schedule. It uses a multi-indicator strategy to trade Gold (XAUUSD), GBP/JPY (GBPJPY), and Bitcoin (BTCUSD) via the Exness broker.

## Core Components

### 1. Exness Client (`exness_client.py`)
- Interfaces with Exness via **MetaApi.cloud**.
- MetaApi provides a REST/WebSocket bridge to MetaTrader 4/5 accounts, allowing Linux-based execution (GitHub Actions).
- Handles fetching market data, account summary, and executing market orders.

### 2. Strategy Engine (`strategy.py`)
- **Technical Indicators**: RSI (14), Fast SMA (20), and Slow SMA (50).
- **Signal Generation**: Requires 2 out of 3 indicator alignment for BUY/SELL signals.
- **Risk Management**: Enforces a strict 1:3 Risk-to-Reward ratio.
- **Position Sizing**: Implements dynamic lot sizing based on account balance tiers.
- **Recursive Learning**: Adjusts a `performance_multiplier` based on historical win rates.

### 3. Database Client (`db_client.py`)
- Uses MongoDB Atlas for persistence.
- **Trades Collection**: Logs every executed trade and updates them upon closure.
- **Learning State Collection**: Stores daily snapshots of performance metrics and instrument-specific statistics.

### 4. Execution Layer (`executor.py`)
- **Async Execution**: Uses Python `asyncio` for MetaApi compatibility.
- **Stealth Execution**: Randomizes entry time (30-290 seconds) within the 5-minute cycle.
- **Circuit Breaker**: Halts trading if daily drawdown exceeds 5% of the starting daily balance.

### 5. Orchestration (`main.py`)
- Entry point for the GitHub Action (Async).
- Manages initialization, execution cycle, trade reconciliation, and learning state updates.

## Setup Instructions

### Prerequisites
1. **Exness Account**: A verified MT4 or MT5 account (e.g., Login: `298682494`, Server: `Exness-MT5Trial9`).
2. **MetaApi Account**: Sign up at [MetaApi.cloud](https://metaapi.cloud/).
3. **Connect Account**:
   - Go to MetaApi Dashboard > "Add Account".
   - Select **MetaTrader 5**.
   - Use your Exness Login, Password, and Server.
   - Once connected, MetaApi will provide a **unique Account ID**.
4. **MongoDB Atlas**: A cluster with a connection string.

### ⚠️ SECURITY WARNING
**Never hardcode your Exness password or MetaApi tokens in the source code.** Always use GitHub Secrets.

### GitHub Secrets Configuration
Store the following in your GitHub repository secrets:
- `META_API_TOKEN`: Your MetaApi token.
- `META_API_ACCOUNT_ID`: The unique Account ID MetaApi assigned to your Exness connection.
- `MONGODB_URI`: Your MongoDB Atlas connection string.

### Local Development
1. Create a `.env` file with the secrets above.
2. Install dependencies: `pip install -r requirements.txt`.
3. Run the bot: `python main.py`.
4. Run tests: `python -m pytest`.

## Workflow
1. GitHub Actions triggers every 5 minutes.
2. Bot connects to MetaApi and fetches latest Exness balance.
3. Bot checks Circuit Breaker status.
4. For each instrument, technical indicators are calculated.
5. If a signal is generated, a randomized delay is applied.
6. Market order is placed via MetaApi with SL/TP.
7. Trade is logged to MongoDB and learning state is updated.
