#!/bin/bash

# Use the PORT environment variable if provided (Render default), otherwise default to 8001
PORT=${PORT:-8001}

# Start FastAPI in the background (Main API)
echo "Starting FastAPI Backend on port $PORT..."
python -m uvicorn app.main:app --host 0.0.0.0 --port $PORT &

# Start the Automated Sales Sync Watcher in the background
echo "Starting Sales Sync Watcher..."
python scripts/sync_watcher.py &

# Start Streamlit in the background/foreground (Dashboard)
# Note: Render only publicly exposes the port defined in $PORT. 
# To access Streamlit, it would need a proxy or to be the primary port.
echo "🚀 Starting AI Cafe Manager Dashboard on port 7860..."
python -m streamlit run ui.py --server.port 7860 --server.address 0.0.0.0
