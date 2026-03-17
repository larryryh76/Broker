#!/bin/bash

# 1. Start Xvfb for headless GUI
rm -f /tmp/.X99-lock
Xvfb :99 -screen 0 1024x768x16 &
export DISPLAY=:99

# 2. Setup MT5 path
MT5_PATH="$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"

# 3. Fallback search for terminal64.exe if standard path fails
if [ ! -f "$MT5_PATH" ]; then
    echo "Terminal not found at default path, searching..."
    MT5_PATH=$(find "$WINEPREFIX/drive_c" -name "terminal64.exe" | head -n 1)
fi

echo "Starting MT5 Terminal at: $MT5_PATH"
wine "$MT5_PATH" /portable /skipupdate &
sleep 30

echo "Starting mt5linux bridge server (inside Wine)..."
# Using 0.0.0.0 to allow cross-container communication
wine python -m mt5linux --host 0.0.0.0 --port 8001 &

# Keep container alive
wait
