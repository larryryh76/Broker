# THE MONEY MACHINE: Dockerized Autonomous MT5 Foundation

This repository provides a professional-grade, fully autonomous architecture for MetaTrader 5 (MT5) trading bots. It is designed to run exclusively on GitHub Actions or equivalent CI/CD platforms using a decoupled multi-service Docker environment.

## Architecture Highlights

- **Decoupled Services**: Separates the MetaTrader 5 environment (Wine/headless) from the trading bot logic (Python 3) using `docker-compose`.
- **mt5linux Bridge**: Employs an RPyC bridge to allow Linux-based Python code to communicate with the Windows-only MetaTrader 5 terminal.
- **Resilient Connectivity**: Features a multi-layered synchronization strategy with a 30-attempt connection retry loop to handle the initialization lag of MT5 under Wine.
- **Pure Cloud Execution**: No local MT5 installation, Windows license, or GUI session required. 100% cloud-native on `ubuntu-latest`.
- **Autonomous Lifecycle**: Implements full trade reconciliation, risk management (circuit breakers), and position management (break-even protection).

## Repository Structure

- `trading-bot/`: Core Python application (bot, strategy, AI engine, risk management).
- `.github/workflows/`: Automation for building Docker images and running trading cycles.
- `docker-compose.yml`: Orchestrates the MT5 terminal and bot services.
- `Dockerfile`: Provisions the trading bot environment.

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

- **Action Logs**: Real-time streaming of bot execution and MT5 terminal logs.
- **Artifacts**: Account snapshots, trade history, and execution logs are uploaded as artifacts after every run.
- **Cloud State**: If MongoDB is configured, the bot persists its learning state and trade history for continuity across runs.

## Disclaimer
Trading involves significant risk. This foundation is provided for educational and developmental purposes.
