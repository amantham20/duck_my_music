#!/bin/bash
# Start Duck My Music GUI
# This script helps launch the GUI on Linux/WSL

cd "$(dirname "$0")"

# Check if winsdk is installed
if ! python3 -c "import winsdk" 2>/dev/null; then
    echo "Installing missing dependencies..."
    python3 -m pip install winsdk
fi

echo "Starting Duck My Music GUI..."
python3 duck_my_music_gui.py
