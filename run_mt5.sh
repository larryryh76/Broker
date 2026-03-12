#!/bin/bash
export DISPLAY=:99
export WINEPREFIX=/app/.wine

# Ensure writable prefix and correct ownership for Wine
mkdir -p $WINEPREFIX
# If running as root (some environments), we skip chown.
# If running as non-root, this ensures we own the mounted volume.
touch $WINEPREFIX/.owner_check || true

# Start Xvfb virtual display
echo "Starting Xvfb..."
Xvfb :99 -screen 0 1024x768x16 &
sleep 5

# Initialize Wine prefix if it's completely empty (not just dir exists)
if [ -z "$(ls -A $WINEPREFIX 2>/dev/null)" ]; then
    echo "Initializing new Wine prefix..."
    wineboot --init
    sleep 10
fi

# Pre-inject MT5 configuration
echo "Injecting MT5 headless configuration..."
python3 /app/trading-bot/mt5_config_injector.py

# Detect persistent MT5 installation
TERMINAL_PATH="$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"

if [ ! -f "$TERMINAL_PATH" ]; then
    echo "First-time setup: Installing MetaTrader 5..."
    wine /app/mt5setup.exe /auto /quit
    sleep 60
else
    echo "Persistent MT5 detected at $TERMINAL_PATH"
fi

# Install pip and MT5 bridge if missing in persistent Python
if [ ! -f "/app/python_win/Scripts/pip.exe" ]; then
    echo "Configuring Windows Python Bridge..."
    wget https://bootstrap.pypa.io/get-pip.py -O /app/get-pip.py
    wine /app/python_win/python.exe /app/get-pip.py
    wine /app/python_win/python.exe -m pip install MetaTrader5 mt5linux
fi

# Launch MetaTrader 5
echo "Launching MetaTrader 5..."
wine "$TERMINAL_PATH" /portable /skipupdate &
sleep 45

# Launch the mt5linux bridge server
echo "Starting MT5 Bridge Server..."
wine /app/python_win/python.exe /app/mt5_bridge.py &

# ROBUST HANDSHAKING: Wait for port 18812 to be ready
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

# Run the Python trading bot
echo "Starting Trading Bot Engine..."
python3 /app/trading-bot/bot.py
