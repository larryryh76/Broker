#!/bin/bash

# Setup MT5 path
MT5_PATH="$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"

# Fallback search for terminal64.exe if standard path fails
if [ ! -f "$MT5_PATH" ]; then
    echo "Terminal not found at default path, searching..."
    MT5_PATH=$(find "$WINEPREFIX/drive_c" -name "terminal64.exe" | head -n 1)
fi

echo "Starting MT5 Terminal at: $MT5_PATH"
# Use xvfb-run for stable display management in production
xvfb-run --server-args="-screen 0 1024x768x24" wine "$MT5_PATH" /portable /skipupdate &

echo "Waiting 45 seconds for MT5 terminal to stabilize..."
sleep 45

echo "Starting mt5linux bridge server (inside Wine)..."
# Using 0.0.0.0 to allow cross-container communication
# Also wrapped in xvfb-run to ensure Wine environment is consistent
xvfb-run --server-args="-screen 0 1024x768x24" wine python -m mt5linux --host 0.0.0.0 --port 8001 &

# Health check loop: Wait for bridge port to open
echo "Monitoring bridge port 8001..."
while ! (printf "" > /dev/tcp/127.0.0.1/8001) 2>/dev/null; do
    echo "Bridge port not yet available, waiting..."
    sleep 5
done

echo "Bridge is UP and listening on port 8001."

# Keep container alive and monitor processes
wait
