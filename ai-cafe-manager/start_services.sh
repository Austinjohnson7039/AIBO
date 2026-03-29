#!/bin/bash

# Start FastAPI in the background
echo "Starting FastAPI Backend on port 8001..."
python -m uvicorn app.main:app --host 0.0.0.0 --port 8001 &

# Start the Automated Sales Sync Watcher in the background
echo "Starting Sales Sync Watcher..."
python scripts/sync_watcher.py &

# Start Streamlit in the foreground (this will keep the container running on HF's required port)
echo "🚀 Starting AI Cafe Manager Dashboard on port 7860..."
python -m streamlit run ui.py --server.port 7860 --server.address 0.0.0.0
