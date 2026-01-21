#!/bin/bash

APP_DIR="/home/ec2-user/leetcode-friends-backend"
PYTHON_PATH="$APP_DIR/venv/bin/python"
GUNICORN_PATH="$APP_DIR/venv/bin/gunicorn"
APP_MODULE="leetcode_friends_backend:app"
WORKERS=4
BIND_ADDRESS="127.0.0.1:5000"

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

cd "$APP_DIR" || { log "ERROR: Failed to navigate to $APP_DIR"; exit 1; }

log "Fetching latest changes from git..."
git fetch origin

LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [ "$LOCAL" = "$REMOTE" ]; then
    log "No updates found. App is up to date."
    exit 0
fi

log "Updates detected! LOCAL: $LOCAL, REMOTE: $REMOTE"

log "Pulling latest changes..."
git pull origin main

if [ $? -ne 0 ]; then
    log "ERROR: Git pull failed!"
    exit 1
fi

log "Git pull successful. Installing/updating dependencies..."

source "$APP_DIR/venv/bin/activate"
pip install -r requirements.txt --quiet

GUNICORN_PIDS=$(pgrep -f "gunicorn.*leetcode_friends_backend:app")

if [ -n "$GUNICORN_PIDS" ]; then
    log "Found running Gunicorn processes: $GUNICORN_PIDS"
    log "Gracefully stopping Gunicorn..."

    pkill -TERM -f "gunicorn.*leetcode_friends_backend:app"
    for i in {1..30}; do
        REMAINING=$(pgrep -f "gunicorn.*leetcode_friends_backend:app")
        if [ -z "$REMAINING" ]; then
            log "Gunicorn stopped gracefully."
            break
        fi
        sleep 1
    done
    
    REMAINING=$(pgrep -f "gunicorn.*leetcode_friends_backend:app")
    if [ -n "$REMAINING" ]; then
        log "WARNING: Gunicorn didn't stop gracefully. Force killing..."
        pkill -9 -f "gunicorn.*leetcode_friends_backend:app"
        sleep 2
    fi
else
    log "No running Gunicorn processes found."
fi
log "Starting Gunicorn with $WORKERS workers on $BIND_ADDRESS..."

nohup "$GUNICORN_PATH" -w $WORKERS -b $BIND_ADDRESS "$APP_MODULE" > /dev/null 2>&1 &

sleep 2

NEW_PIDS=$(pgrep -f "gunicorn.*leetcode_friends_backend:app")
if [ -n "$NEW_PIDS" ]; then
    log "SUCCESS: Gunicorn restarted successfully (PIDs: $NEW_PIDS)"
    log "Deployment completed successfully!"
else
    log "ERROR: Failed to start Gunicorn!"
    exit 1
fi

