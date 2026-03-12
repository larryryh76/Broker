#!/bin/bash

# SECTION 13 — RUNTIME STABILIZATION & UNIFIED PATHS
export WINEPREFIX=/tmp/wine
export WINEARCH=win64
export DISPLAY=:99

# 1. Initialize writable Wine prefix in /tmp
echo "Initializing dynamic Wine prefix in /tmp/wine..."
mkdir -p /tmp/wine
wineboot --init
sleep 10

# 2. Start Xvfb virtual display
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1024x768x16 &
sleep 3

# 3. Pre-inject MT5 configuration (MUST HAPPEN BEFORE LAUNCH)
echo "Injecting MT5 headless configuration..."
python3 /app/trading-bot/mt5_config_injector.py

# 4. Handle MT5 Terminal Installation
# Using unified path /app/mt5_terminal
TERMINAL_PATH="/app/mt5_terminal/terminal64.exe"

if [ ! -f "$TERMINAL_PATH" ]; then
    echo "Installing MetaTrader 5..."
    wine /app/mt5setup.exe /auto /quit
    sleep 60
    # Copy from default wine location to unified path if needed
    if [ ! -f "$TERMINAL_PATH" ]; then
        mkdir -p /app/mt5_terminal
        cp -r "$WINEPREFIX/drive_c/Program Files/MetaTrader 5/." /app/mt5_terminal/
    fi
fi

# 5. Launch MetaTrader 5 in Portable Mode
echo "Launching MetaTrader 5 (Portable)..."
wine "$TERMINAL_PATH" /portable /skipupdate &
sleep 20

# 6. Launch the mt5linux bridge server
echo "Starting MT5 Bridge Server..."
wine /app/python_win/python.exe /app/mt5_bridge.py &

# 7. ROBUST HANDSHAKING: Wait for port 18812 to be ready
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

# 8. Run the Python autonomous trading machine
echo "Starting Autonomous AI Machine Engine..."
python3 /app/trading-bot/bot.py
