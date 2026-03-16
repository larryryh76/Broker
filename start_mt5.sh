#!/bin/bash

# 1. Start Xvfb for headless GUI
Xvfb :99 -screen 0 1024x768x16 &
export DISPLAY=:99

# 2. Setup MT5
MT5_PATH="$HOME/.wine/drive_c/Program Files/MetaTrader 5/terminal64.exe"
if [ ! -f "$MT5_PATH" ]; then
    echo "Installing MT5..."
    wine mt5setup.exe /auto /quit
    sleep 60
fi

# 3. Setup Windows Python in Wine (for bridge server)
WINE_PYTHON="wine python"
if ! wine python --version > /dev/null 2>&1; then
    echo "Installing Windows Python in Wine..."
    wine python-3.10.11-amd64.exe /quiet InstallAllUsers=1 PrependPath=1
    sleep 60
    # Install MetaTrader5 and mt5linux inside Wine Python
    wine python -m pip install --upgrade pip
    wine python -m pip install MetaTrader5 mt5linux rpyc==4.1.5
fi

echo "Starting MT5 Terminal..."
wine "$MT5_PATH" /portable /skipupdate &
sleep 20

echo "Starting mt5linux bridge server (inside Wine)..."
# The bridge server must run where the MetaTrader5 library is available
wine python -m mt5linux --host 0.0.0.0 --port 8001 &

# Keep container alive
wait
