# THE MONEY MACHINE: Native MT5 Cloud Foundation

This repository provides a professional-grade, fully autonomous architecture for MetaTrader 5 (MT5) trading bots, optimized for stability and performance on GitHub Actions using native Windows runners.

## Architecture Highlights

- **Native Windows Execution**: Runs directly on `windows-latest` runners, eliminating the overhead and instability of emulation layers like Wine or Docker.
- **Official MetaTrader 5 Integration**: Utilizes the official `MetaTrader5` Python package for direct, low-latency communication with the terminal.
- **Automated Lifecycle**: Implements full trade reconciliation, risk management (circuit breakers), and position management (break-even protection).
- **Pure Cloud Execution**: No local MT5 installation or manual intervention required. 100% cloud-native via GitHub Actions.
- **Persistent State**: Integrates with MongoDB Atlas to maintain learning states and trade history across ephemeral CI runs.

## Repository Structure

- `trading_bot/`: Core Python application (bot, strategy, AI engine, risk management).
- `.github/workflows/`: Automation for running 15-minute trading cycles.

## Setup & Deployment

### 1. GitHub Secrets
Configure the following secrets in your repository:
- `MT5_LOGIN`: MT5 account number.
- `MT5_PASSWORD`: MT5 trading password.
- `MT5_SERVER`: Broker's server name.
- `MONGODB_URI`: (Optional) MongoDB Atlas connection string for persistence.

### 2. Execution
The system is scheduled to run every 15 minutes via GitHub Actions. You can manually trigger a run via **Workflow Dispatch** in the **Actions** tab.

## Monitoring

- **Action Logs**: Real-time streaming of bot execution and MT5 terminal status.
- **Artifacts**: Account snapshots, trade history, and execution logs are uploaded as artifacts after every run.
- **Cloud State**: If MongoDB is configured, the bot persists its learning state and trade history for continuity across runs.

## Disclaimer
Trading involves significant risk. This foundation is provided for educational and developmental purposes.
