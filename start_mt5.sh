#!/bin/bash

# 1. Start Xvfb for headless GUI
Xvfb :99 -screen 0 1024x768x16 &
export DISPLAY=:99

# 2. Setup MT5 path
MT5_PATH="/root/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"

echo "Starting MT5 Terminal..."
wine "$MT5_PATH" /portable /skipupdate &
sleep 30

echo "Starting mt5linux bridge server (inside Wine)..."
wine python -m mt5linux --host 0.0.0.0 --port 8001 &
sleep 30

echo "Starting autonomous trading bot..."
# Run the bot in the background so we can wait on all processes
python3 trading-bot/bot.py &

# Keep container alive and wait for processes
wait -n

# Exit code of the first process to exit
exit $?
