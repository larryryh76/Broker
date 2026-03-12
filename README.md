# THE MONEY MACHINE: GitHub-Native Foundation

This repository provides a stable, fully autonomous foundation for MetaTrader 5 (MT5) trading bots running exclusively on GitHub Actions. It has been refactored to remove complex Docker/Wine layers and focus on a robust, native foundation.

## Foundation Features

- **Direct MT5 Integration**: Uses the official `MetaTrader5` Python library on `windows-latest` runners.
- **Pure GitHub Workflow**: No external servers or manual setup required. 100% cloud-native.
- **Autonomous Authentication**: Pre-seeds `terminal.ini` and `common.ini` to bypass GUI hangs and enable Algo-Trading automatically.
- **Persistent Snapshots**: Periodically captures account status (balance, equity, margin) and saves them as GitHub artifacts and cloud state (if MongoDB is configured).
- **Workspace-Local Terminal**: Installs and caches the MT5 terminal directly within the repository workspace (`mt5_terminal/`).

## Project Cleanup Summary

The following complex/broken components have been removed to ensure stability:
- **Docker/Container Architecture**: Eliminated `Dockerfile` and Wine-based orchestration which caused permission and IPC errors.
- **Wine Bridges**: Removed `mt5linux` and cross-platform bridge servers in favor of native Windows stability.
- **System-Wide Dependencies**: Transitioned to workspace-local installations to avoid environment pollution.

## Setup Instructions

### 1. GitHub Secrets
Configure these secrets in your repository:
- `MT5_LOGIN`: Your MT5 account number.
- `MT5_PASSWORD`: Your trading password.
- `MT5_SERVER`: Your broker's server name (e.g., `FBS-Real`).
- `MONGODB_URI`: (Optional) MongoDB Atlas connection string for persistent state.

### 2. Automation
The bot runs every 15 minutes by default. You can manually trigger a run via the **Actions** tab using **Workflow Dispatch**.

## Adding AI Strategies

To extend this foundation into a full AI trading machine:
1. **Indicator Module**: Add technical analysis functions in a new `indicators.py` or extend `strategy.py`.
2. **AI Integration**: Re-introduce `ai_model.py` for signal prediction using the validated `TerminalConnector` to fetch historical candles.
3. **Execution Logic**: Extend the `execute_order` method in `TerminalConnector` to implement your trading rules.

## Disclaimer
Past performance does not guarantee future results. Trading involves significant risk.
