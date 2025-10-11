#!/bin/bash

# Script to stop Gunicorn gracefully

# Find all gunicorn processes for this app
GUNICORN_PIDS=$(pgrep -f "gunicorn.*leetcode_friends_backend:app")

if [ -z "$GUNICORN_PIDS" ]; then
    echo "No Gunicorn processes found for leetcode_friends_backend:app"
    echo "Check with: ps aux | grep gunicorn"
    exit 0
fi

echo "Found Gunicorn processes: $GUNICORN_PIDS"
echo "Gracefully stopping Gunicorn..."

# Send SIGTERM for graceful shutdown
pkill -TERM -f "gunicorn.*leetcode_friends_backend:app"

# Wait for processes to finish (max 30 seconds)
for i in {1..30}; do
    REMAINING=$(pgrep -f "gunicorn.*leetcode_friends_backend:app")
    if [ -z "$REMAINING" ]; then
        echo "Gunicorn stopped gracefully."
        exit 0
    fi
    sleep 1
done

# Force kill if still running
REMAINING=$(pgrep -f "gunicorn.*leetcode_friends_backend:app")
if [ -n "$REMAINING" ]; then
    echo "WARNING: Gunicorn didn't stop gracefully. Force killing..."
    pkill -9 -f "gunicorn.*leetcode_friends_backend:app"
    sleep 1
    echo "Gunicorn force killed."
fi

