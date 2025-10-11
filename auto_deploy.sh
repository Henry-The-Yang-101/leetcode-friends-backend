#!/bin/bash

# Auto-deployment script for LeetCode Friends Backend
# This script checks for git updates and gracefully restarts the Flask app if changes are detected

# Configuration
APP_DIR="/home/ec2-user/leetcode-friends-backend"
PYTHON_PATH="$APP_DIR/venv/bin/python"
GUNICORN_PATH="$APP_DIR/venv/bin/gunicorn"
APP_MODULE="leetcode_friends_backend:app"
WORKERS=4
BIND_ADDRESS="127.0.0.1:5000"

# Log function
log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Navigate to app directory
cd "$APP_DIR" || { log "ERROR: Failed to navigate to $APP_DIR"; exit 1; }

# Fetch latest changes
log "Fetching latest changes from git..."
git fetch origin

# Check if there are updates
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)  # Change to 'master' if that's your default branch

if [ "$LOCAL" = "$REMOTE" ]; then
    log "No updates found. App is up to date."
    exit 0
fi

log "Updates detected! LOCAL: $LOCAL, REMOTE: $REMOTE"

# Pull the latest changes
log "Pulling latest changes..."
git pull origin main  # Change to 'master' if needed

if [ $? -ne 0 ]; then
    log "ERROR: Git pull failed!"
    exit 1
fi

log "Git pull successful. Installing/updating dependencies..."

# Activate virtual environment and update dependencies
source "$APP_DIR/venv/bin/activate"
pip install -r requirements.txt --quiet

# Check if Gunicorn is running and stop it gracefully
GUNICORN_PIDS=$(pgrep -f "gunicorn.*leetcode_friends_backend:app")

if [ -n "$GUNICORN_PIDS" ]; then
    log "Found running Gunicorn processes: $GUNICORN_PIDS"
    log "Gracefully stopping Gunicorn..."
    
    # Send SIGTERM to all gunicorn processes for graceful shutdown
    pkill -TERM -f "gunicorn.*leetcode_friends_backend:app"
    
    # Wait for processes to finish (max 30 seconds)
    for i in {1..30}; do
        REMAINING=$(pgrep -f "gunicorn.*leetcode_friends_backend:app")
        if [ -z "$REMAINING" ]; then
            log "Gunicorn stopped gracefully."
            break
        fi
        sleep 1
    done
    
    # Force kill if still running
    REMAINING=$(pgrep -f "gunicorn.*leetcode_friends_backend:app")
    if [ -n "$REMAINING" ]; then
        log "WARNING: Gunicorn didn't stop gracefully. Force killing..."
        pkill -9 -f "gunicorn.*leetcode_friends_backend:app"
        sleep 2
    fi
else
    log "No running Gunicorn processes found."
fi

# Start Gunicorn with new code
log "Starting Gunicorn with $WORKERS workers on $BIND_ADDRESS..."

# Use nohup to start gunicorn in background
nohup "$GUNICORN_PATH" -w $WORKERS -b $BIND_ADDRESS "$APP_MODULE" > /dev/null 2>&1 &

sleep 2

# Verify it started successfully
NEW_PIDS=$(pgrep -f "gunicorn.*leetcode_friends_backend:app")
if [ -n "$NEW_PIDS" ]; then
    log "SUCCESS: Gunicorn restarted successfully (PIDs: $NEW_PIDS)"
    log "Deployment completed successfully!"
else
    log "ERROR: Failed to start Gunicorn!"
    exit 1
fi

