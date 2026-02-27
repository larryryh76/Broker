# THE MONEY MACHINE - Architecture Documentation

## Overview
THE MONEY MACHINE is a production-ready, serverless trading bot designed to execute on a GitHub Actions schedule. It uses a multi-indicator strategy to trade Gold (XAU/USD), GBP/JPY, and Bitcoin (BTC/USD).

## Core Components

### 1. Oanda Client (`oanda_client.py`)
- Interfaces with OANDA v20 REST API.
- Handles fetching market data (candlesticks), account summary, and executing market orders.
- Includes methods for fetching open and closed trades for reconciliation.

### 2. Strategy Engine (`strategy.py`)
- **Technical Indicators**: RSI (14), Fast SMA (20), and Slow SMA (50).
- **Signal Generation**: Requires 2 out of 3 indicator alignment for BUY/SELL signals.
- **Risk Management**: Enforces a strict 1:3 Risk-to-Reward ratio.
- **Position Sizing**: Implements dynamic lot sizing based on account balance tiers:
  - < $100: 2% Risk
  - $100 - $1000: 3% Risk
  - $1000 - $10000: 5% Risk
  - > $10000: 8% Risk
- **Confidence Adjustment**: Scales position size based on signal confidence.

### 3. Database Client (`db_client.py`)
- Uses MongoDB Atlas for persistence.
- **Trades Collection**: Logs every executed trade and updates them upon closure.
- **Learning State Collection**: Stores daily snapshots of performance metrics (Win Rate, Daily P&L) and instrument-specific statistics.

### 4. Execution Layer (`executor.py`)
- **Stealth Execution**: Randomizes entry time (30-290 seconds) within the 5-minute cycle.
- **Circuit Breaker**: Halts trading if daily drawdown exceeds 5% of the starting daily balance.
- **Margin Check**: Basic check to prevent trading high-margin instruments (XAU, BTC) with extremely low balance ($<10).

### 5. Orchestration (`main.py`)
- Entry point for the GitHub Action.
- Manages initialization, execution cycle, trade reconciliation, and learning state updates.

## Recursive Learning System
The bot implements a self-improving feedback loop:
1. **Performance Tracking**: After each cycle, the bot reconciles closed trades from OANDA and updates its MongoDB learning state with the actual P&L and Win Rate.
2. **Parameter Adjustment**: At the start of each cycle, the `Executor` fetches the latest learning state.
3. **Dynamic Scaling**: The `Strategy` adjusts a `performance_multiplier` based on the historical win rate:
   - Win Rate > 60% (with 10+ trades): Multiplier increases to 1.2x (Aggressive).
   - Win Rate < 40% (with 10+ trades): Multiplier decreases to 0.8x (Conservative).
   - This multiplier directly scales the calculated position size.

## Setup Instructions

### Prerequisites
- OANDA v20 Practice or Live Account.
- MongoDB Atlas Cluster.
- GitHub Repository for deployment.

### GitHub Secrets Configuration
Store the following in your GitHub repository secrets:
- `OANDA_TOKEN`: Your OANDA API Bearer Token.
- `OANDA_ACCOUNT_ID`: Your OANDA Account ID.
- `MONGODB_URI`: Your MongoDB Atlas connection string.

### Local Development
1. Create a `.env` file with the secrets above.
2. Install dependencies: `pip install -r requirements.txt`.
3. Run the bot: `python main.py`.
4. Run tests: `python -m pytest`.

## Workflow
1. GitHub Actions triggers every 5 minutes.
2. Bot fetches latest balance and learning state.
3. Bot checks Circuit Breaker status.
4. For each instrument, technical indicators are calculated.
5. If a signal is generated, a randomized delay is applied.
6. Market order is placed with SL/TP.
7. Trade is logged to MongoDB.
8. Learning state is updated and open trades are reconciled with closed trades in OANDA.
