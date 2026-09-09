#!/bin/bash

# Script to start Gunicorn for LeetCode Friends Backend

# APP_DIR="/home/ec2-user/leetcode-friends-backend" <- ec2
APP_DIR="/home/hhenryyangg/leetcode-friends-backend" <- gcp
GUNICORN_PATH="$APP_DIR/venv/bin/gunicorn"
APP_MODULE="leetcode_friends_backend:app"
# NOTE: gunicorn's built-in load balancer has no sticky-session support, so
# when using the eventlet worker for Flask-SocketIO only a single worker
# process is supported. Do NOT increase this - see
# https://flask-socketio.readthedocs.io/en/latest/deployment.html#gunicorn-web-server
WORKERS=1
WORKER_CLASS="eventlet"
BIND_ADDRESS="127.0.0.1:5000"

cd "$APP_DIR" || { echo "ERROR: Failed to navigate to $APP_DIR"; exit 1; }

# Activate virtual environment
source "$APP_DIR/venv/bin/activate"

# Check if already running
EXISTING_PIDS=$(pgrep -f "gunicorn.*leetcode_friends_backend:app")
if [ -n "$EXISTING_PIDS" ]; then
    echo "Gunicorn is already running (PIDs: $EXISTING_PIDS)"
    echo "Use ./stop_gunicorn.sh to stop it first"
    exit 0
fi

# Start Gunicorn with nohup
# The eventlet worker class is required for Flask-SocketIO's WebSocket transport
# (Socket.IO signaling relay) to work correctly across workers.
echo "Starting Gunicorn with $WORKERS $WORKER_CLASS workers on $BIND_ADDRESS..."
nohup "$GUNICORN_PATH" -w $WORKERS -k $WORKER_CLASS -b $BIND_ADDRESS "$APP_MODULE" > /dev/null 2>&1 &

sleep 2

# Verify it started
NEW_PIDS=$(pgrep -f "gunicorn.*leetcode_friends_backend:app")
if [ -n "$NEW_PIDS" ]; then
    echo "SUCCESS: Gunicorn started (PIDs: $NEW_PIDS)"
    echo ""
    echo "Check status with: ps aux | grep gunicorn"
else
    echo "ERROR: Failed to start Gunicorn!"
    exit 1
fi

