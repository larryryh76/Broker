#!/bin/bash

# SECTION 11 — INFRASTRUCTURE STABILIZATION FIXES
export WINEPREFIX=/app/.wine
export WINEARCH=win64
export DISPLAY=:99

# 1. Fix Xvfb display permissions
echo "Setting up Xvfb permissions..."
mkdir -p /tmp/.X11-unix
chmod 1777 /tmp/.X11-unix

# 2. Start Xvfb virtual display
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1024x768x16 &
sleep 5

# 3. Recreate Wine prefix to solve ownership/corruption errors
echo "Recreating Wine prefix..."
rm -rf $WINEPREFIX
wineboot --init
# Ensure full permissions for the non-root botuser
chmod -R 777 $WINEPREFIX
sleep 10

# 4. Pre-inject MT5 configuration
echo "Injecting MT5 headless configuration..."
python3 /app/trading-bot/mt5_config_injector.py

# 5. Runtime dependencies and MT5 Setup
if [ ! -f "/app/python_win/Scripts/pip.exe" ]; then
    echo "Configuring Windows Python Bridge..."
    wget https://bootstrap.pypa.io/get-pip.py -O /app/get-pip.py
    wine /app/python_win/python.exe /app/get-pip.py
    wine /app/python_win/python.exe -m pip install MetaTrader5 mt5linux
fi

# Ensure terminal exists (from persistent cache or fresh install)
# Note: User requested wine /app/mt5_terminal/terminal64.exe /portable &
TERMINAL_PATH="/app/mt5_terminal/terminal64.exe"
if [ ! -f "$TERMINAL_PATH" ]; then
    echo "Installing MetaTrader 5..."
    wine /app/mt5setup.exe /auto /quit
    sleep 60
fi

# 6. Launch MT5 before bridge server
echo "Launching MetaTrader 5..."
wine "$TERMINAL_PATH" /portable /skipupdate &
# Allow MT5 to fully stabilize
sleep 60

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
python3 /app/trading-bot/bot.py
