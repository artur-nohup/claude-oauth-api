#!/bin/bash

# Start Xvfb (virtual display)
echo "Starting Xvfb on display :99..."
Xvfb :99 -screen 0 1280x720x24 -ac &
XVFB_PID=$!

# Wait for Xvfb to start
sleep 2

# Start fluxbox window manager (lightweight)
echo "Starting window manager..."
DISPLAY=:99 fluxbox &
FLUXBOX_PID=$!

# Start x11vnc without password for easy access
echo "Starting VNC server on port 5900..."
x11vnc -display :99 -nopw -forever -shared -rfbport 5900 &
VNC_PID=$!

# Give VNC time to start
sleep 2

echo "VNC server started. Connect to port 5900 to see the browser"
echo "No password required for VNC connection"

# Start the FastAPI application
echo "Starting Claude OAuth API..."
export DISPLAY=:99
python main_visual.py

# Cleanup on exit
kill $XVFB_PID $FLUXBOX_PID $VNC_PID 2>/dev/null
