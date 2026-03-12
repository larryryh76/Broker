#!/bin/bash

# SECTION 14 — DYNAMIC RUNNER HOME PREFIX FIX
export WINEPREFIX="$HOME/.wine"
export WINEARCH=win64
export DISPLAY=:99

# 1. Kill any previous Xvfb instance and cleanup locks
echo "Cleaning up Xvfb..."
pkill Xvfb || true
rm -f /tmp/.X99-lock || true
sleep 1

# 2. Start Xvfb virtual display
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1024x768x16 &
sleep 3

# 3. Create Wine prefix owned by the GitHub runner
echo "Initializing dynamic Wine prefix in $WINEPREFIX..."
rm -rf "$WINEPREFIX" || true
mkdir -p "$WINEPREFIX"
wineboot --init
sleep 10

# 4. Pre-inject MT5 configuration (MUST HAPPEN BEFORE LAUNCH)
echo "Injecting MT5 headless configuration..."
python3 /app/trading-bot/mt5_config_injector.py

# 5. Runtime dependencies setup (only if missing in persistent python)
if [ ! -f "/app/python_win/Scripts/pip.exe" ]; then
    echo "Configuring Windows Python Bridge..."
    wget https://bootstrap.pypa.io/get-pip.py -O /app/get-pip.py
    wine /app/python_win/python.exe /app/get-pip.py
    wine /app/python_win/python.exe -m pip install MetaTrader5 mt5linux pywin32
fi

# 6. Launch MT5 in Portable Mode
# Path as requested by user
TERMINAL_PATH="$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"

# If terminal missing from prefix, install it
if [ ! -f "$TERMINAL_PATH" ]; then
    echo "Installing MetaTrader 5..."
    wine /app/mt5setup.exe /auto /quit
    sleep 60
fi

echo "Launching MetaTrader 5 (Portable)..."
wine "$TERMINAL_PATH" /portable /skipupdate &
sleep 20

# 7. Launch the mt5linux bridge server
echo "Starting MT5 Bridge Server..."
wine /app/python_win/python.exe /app/mt5_bridge.py &

# 8. ROBUST HANDSHAKING: Wait for port 18812 to be ready
echo "Waiting for bridge server to respond on port 18812..."
MAX_RETRIES=30
COUNT=0
while ! nc -z localhost 18812; do
  COUNT=$((COUNT + 1))
  if [ $COUNT -ge $MAX_RETRIES ]; then
    echo "ERROR: Bridge server failed to start within 30 seconds."
    exit 1
  fi
  sleep 1
done
echo "Bridge server is READY."

# 9. Run the Python autonomous trading machine
echo "Starting Autonomous AI Machine Engine..."
# Ensure logs directories exist
mkdir -p /app/trading-bot/logs /app/trading-bot/trades /app/trading-bot/data
python3 /app/trading-bot/bot.py
