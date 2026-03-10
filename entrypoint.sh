#!/bin/bash

# Start Xvfb virtual display
Xvfb :99 -screen 0 1024x768x16 &
export DISPLAY=:99

# Launch MetaTrader 5 in the background
# We use the pre-installed path in the Wine prefix
echo "Launching MetaTrader 5..."
wine "C:\\Program Files\\MetaTrader 5\\terminal64.exe" /portable /skipupdate &

# Wait for MT5 initialization and connection
sleep 60

# Run the Python trading bot using the Wine-based Windows Python
echo "Starting Trading Bot..."
wine python /app/trading-bot/bot.py
