#!/bin/bash

# 1. Start Xvfb for headless GUI
rm -f /tmp/.X99-lock
Xvfb :99 -screen 0 1024x768x16 &
export DISPLAY=:99

# 2. Setup MT5 path
MT5_PATH="/root/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"

echo "Starting MT5 Terminal..."
wine "$MT5_PATH" /portable /skipupdate &
sleep 30

echo "Starting mt5linux bridge server (inside Wine)..."
wine python -m mt5linux --host 0.0.0.0 --port 8001 &

# Keep container alive
wait
