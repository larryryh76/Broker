#!/bin/bash
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x16 &
sleep 5

# Ensure Wine prefix is initialized (if not already during build)
if [ ! -d "$WINEPREFIX" ]; then
    echo "Initializing Wine prefix..."
    wineboot --init
    sleep 10
fi

# Pre-inject MT5 configuration (enable Algo Trading, seeded login)
echo "Injecting MT5 headless configuration..."
python3 /app/trading-bot/mt5_config_injector.py

# Install MetaTrader 5 if missing
TERMINAL_PATH="$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"
if [ ! -f "$TERMINAL_PATH" ]; then
    echo "Installing MetaTrader 5..."
    wine /app/mt5setup.exe /auto /quit
    sleep 45
fi

# Install pip and bridge dependencies inside Wine
if [ ! -f "/app/python_win/Scripts/pip.exe" ]; then
    echo "Installing bridge dependencies inside Wine..."
    wget https://bootstrap.pypa.io/get-pip.py -O /app/get-pip.py
    wine /app/python_win/python.exe /app/get-pip.py
    wine /app/python_win/python.exe -m pip install MetaTrader5 mt5linux
fi

# Launch MetaTrader 5
echo "Launching MetaTrader 5..."
wine "$TERMINAL_PATH" /portable /skipupdate &
sleep 60

# Launch the mt5linux bridge server
echo "Starting MT5 Bridge Server..."
wine /app/python_win/python.exe /app/mt5_bridge.py &
sleep 20

# Run the Python trading bot
echo "Starting Trading Bot (Native Linux)..."
python3 /app/trading-bot/bot.py
