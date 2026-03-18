#!/bin/bash

# Setup MT5 path
MT5_PATH="$WINEPREFIX/drive_c/Program Files/MetaTrader 5/terminal64.exe"

# Fallback search for terminal64.exe if standard path fails
if [ ! -f "$MT5_PATH" ]; then
    echo "Terminal not found at default path, searching..."
    MT5_PATH=$(find "$WINEPREFIX/drive_c" -name "terminal64.exe" | head -n 1)
fi

echo "Starting MT5 Terminal at: $MT5_PATH"
# Use xvfb-run for stable display management
xvfb-run -a wine "$MT5_PATH" /portable /skipupdate &

echo "Waiting 60 seconds for MT5 terminal to stabilize..."
sleep 60

# Function to start the bridge
start_bridge() {
    echo "Starting mt5linux bridge server (inside Wine)..."
    xvfb-run -a wine python -m mt5linux --host 0.0.0.0 --port 8001 &
}

start_bridge

# Health check loop: Wait for bridge port to open
echo "Monitoring bridge port 8001..."
while true; do
    if (printf "" > /dev/tcp/127.0.0.1/8001) 2>/dev/null; then
        echo "Bridge is UP and listening on port 8001."
        # Keep bridge healthy
        sleep 30
    else
        echo "Bridge port 8001 not available. Attempting restart..."
        start_bridge
        sleep 15
    fi
done

# Keep container alive and monitor processes
wait
