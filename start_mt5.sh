#!/bin/bash
set -e

# Clear locks
rm -f /tmp/.X99-lock

# Start Xvfb
Xvfb :99 -screen 0 1024x768x24 &
sleep 5

# Set path to MT5
MT5_PATH="/root/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"

if [ ! -f "$MT5_PATH" ]; then
    echo "MT5 not found at $MT5_PATH. Searching..."
    MT5_PATH=$(find /root/.wine/drive_c -name "terminal64.exe" | head -n 1)
fi

echo "Starting MetaTrader 5 at $MT5_PATH..."
wine "$MT5_PATH" /portable /skipupdate &

# Wait for MT5 to stabilize
echo "Waiting for MT5 to start (60s)..."
sleep 60

echo "Starting mt5linux bridge server..."
# Use 0.0.0.0 to allow cross-container connection
wine python -m mt5linux --host 0.0.0.0 --port 8001 &

# Health check loop
echo "Monitoring bridge port 8001..."
while true; do
    if nc -z localhost 8001; then
        echo "Bridge is UP."
        sleep 60
    else
        echo "Bridge is DOWN. Restarting bridge..."
        wine python -m mt5linux --host 0.0.0.0 --port 8001 &
        sleep 10
    fi
done

wait
