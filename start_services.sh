#!/bin/bash

# Use the PORT environment variable if provided (Render default), otherwise default to 8001
PORT=${PORT:-8001}

# 1. Start the Automated Sales Sync Watcher in the background
echo "Starting Sales Sync Watcher..."
python scripts/sync_watcher.py &

# 2. Start FastAPI Backend as the primary process (foreground)
echo "🚀 Starting AI Cafe Manager Backend on port $PORT..."
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT
