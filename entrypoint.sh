#!/bin/bash

# Start Xvfb virtual display
Xvfb :99 -screen 0 1024x768x16 &
export DISPLAY=:99

# Initialize Wine prefix if it doesn't exist
if [ ! -d "$WINEPREFIX" ]; then
    echo "Initializing Wine prefix..."
    wineboot --init
    sleep 10
fi

# Install MT5 if not already present in the Wine prefix
TERMINAL_PATH="$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"
if [ ! -f "$TERMINAL_PATH" ]; then
    echo "Installing MetaTrader 5..."
    wine /app/mt5setup.exe /auto /quit
    # Wait for installation to complete
    sleep 45
fi

# Launch MetaTrader 5 in the background via Wine
echo "Launching MetaTrader 5..."
wine "$TERMINAL_PATH" /portable /skipupdate &
# Allow MT5 to fully initialize
sleep 60

# Launch the mt5linux bridge server inside Wine
echo "Starting MT5 Bridge Server..."
wine /app/python_win/python.exe /app/mt5_bridge.py &
# Allow bridge to connect to MT5
sleep 20

# Run the Python trading bot using native Linux Python
echo "Starting Trading Bot (Native Linux)..."
python3 /app/trading-bot/bot.py
