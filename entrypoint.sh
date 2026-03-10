#!/bin/bash

# Start Xvfb virtual display
Xvfb :99 -screen 0 1024x768x16 &
export DISPLAY=:99

# Launch MetaTrader 5 in the background via Wine
echo "Launching MetaTrader 5..."
wine "C:\\Program Files\\MetaTrader 5\\terminal64.exe" /portable /skipupdate &
sleep 30

# Launch the mt5linux bridge server inside Wine
echo "Starting MT5 Bridge Server..."
wine /app/python_win/python.exe /app/mt5_bridge.py &
sleep 15

# Run the Python trading bot using native Linux Python
echo "Starting Trading Bot (Native Linux)..."
python3 /app/trading-bot/bot.py
