#!/bin/bash

# Setup MT5 path
MT5_PATH="$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"

# Fallback search for terminal64.exe if standard path fails
if [ ! -f "$MT5_PATH" ]; then
    echo "Terminal not found at default path, searching..."
    MT5_PATH=$(find "$WINEPREFIX/drive_c" -name "terminal64.exe" | head -n 1)
fi

# Ensure permissions (although already set in Dockerfile, this is a safety net)
# As we run as trader, we can't chown root files, but we should own our prefix.
# chown -R trader:trader /home/trader/.wine # Only if script runs as root

# 1. Start Xvfb for headless GUI
rm -f /tmp/.X99-lock
Xvfb :99 -screen 0 1024x768x24 &
export DISPLAY=:99

echo "Starting MT5 Terminal at: $MT5_PATH"
wine "$MT5_PATH" /portable /skipupdate &

echo "Waiting 60 seconds for MT5 terminal to stabilize..."
sleep 60

echo "Starting mt5linux bridge server (inside Wine)..."
# Using 0.0.0.0 to allow cross-container communication
wine python -m mt5linux --host 0.0.0.0 --port 8001 &

# Health check loop: Wait for bridge port to open
echo "Monitoring bridge port 8001..."
# Use nc if available, otherwise fallback to /dev/tcp
for i in {1..30}; do
    if (printf "" > /dev/tcp/127.0.0.1/8001) 2>/dev/null; then
        echo "Bridge is UP and listening on port 8001."
        break
    fi
    echo "Attempt $i: Bridge port not yet available, waiting..."
    sleep 5
done

# Keep container alive and monitor processes
wait
