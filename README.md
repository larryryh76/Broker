# THE MONEY MACHINE: AI-Powered Forex Trading Bot

This repository contains a fully automated, AI-driven Forex trading bot designed for production execution on GitHub Actions. It implements the **Supreme Authority Layer** logic: flipping a $5 virtual seed into millions through aggressive geometric compounding and recursive machine learning.

## Core Features

- **Virtual Sub-Capital Model**: Isolates a $5.00 starting capital from the broker's main balance. All risk, sizing, and targets are calculated from this virtual base.
- **Outcome Dominance Strategy**: Uses a weighted scoring system (Trend, RSI, AI Probability) to authorize trades only when a clear edge is identified.
- **Pure Headless Execution**: Optimized for GitHub Actions (Windows runners) with automated MT5 terminal installation and configuration injection (enabling Algo-Trading and bypassing GUI hangs).
- **Stealth Execution**: Randomizes entry timing (30–290s delay) within the 5-minute cycle to avoid institutional pattern detection.
- **Risk Intelligence**:
  - **$0.05 Safety Switch**: Moves Stop Loss to break-even once a tiny profit threshold is reached.
  - **5% Daily Circuit Breaker**: Halts all operations if the daily drawdown limit is hit.
  - **Magic Number Filtering**: Strictly manages only bot-opened trades (Magic: 123456).
- **Recursive Learning**: Persists state (Day count, virtual equity, instrument performance) in MongoDB Atlas to adapt across ephemeral GHA runs.

## Folder Structure

```
/trading-bot
    bot.py                - Main orchestration engine
    strategy.py           - Signal generation & Outcome Dominance logic
    ai_model.py           - Machine learning classifier (Random Forest)
    risk_management.py    - Capital protection & circuit breaker
    terminal_connector.py - Robust MT5 IPC bridge
    db_client.py          - MongoDB Atlas persistence layer
    mt5_config_injector.py - Headless environment setup
    config.py             - System-wide settings
    requirements.txt      - Python dependencies
.github/workflows/trading-bot.yml - GitHub Actions schedule
```

## Setup Instructions

### 1. Broker Requirements
Requires a MetaTrader 5 account (e.g., FBS or Exness).

### 2. GitHub Secrets
Configure the following secrets in your repository:
- `MT5_LOGIN`: Account number
- `MT5_PASSWORD`: Trading password
- `MT5_SERVER`: Broker server name (e.g., `FBS-Real`)
- `MONGODB_URI`: MongoDB Atlas connection string

### 3. Deployment
The bot is pre-configured to run every 5 minutes. To trigger a manual run, go to the **Actions** tab and use **Workflow Dispatch**.

## Compounding Sequence

The bot follows a 10x-scaling trajectory after the initial flip:
- **Phase 1**: Flip $5 to $50 (micro-lot scaling).
- **Phase 2**: Geometric growth ($50 -> $250 -> $1500 -> $10500...).

## Disclaimer
Trading involves significant risk. This system is for educational purposes. Past performance does not guarantee future results.
