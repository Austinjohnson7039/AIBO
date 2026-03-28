# Use an official Python runtime as a parent image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV BACKEND_URL=http://localhost:8001

# Set work directory
WORKDIR /app

# Install system dependencies (for watchdog and other tools)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Create directories for persistent data if they don't exist
RUN mkdir -p data/sync/incoming data/sync/archive faiss_index

# Copy the start script and make it executable
COPY start_services.sh /usr/local/bin/start_services.sh
RUN chmod +x /usr/local/bin/start_services.sh

# Expose ports (FastAPI=8001, Streamlit=8501)
EXPOSE 8001 8501

# Entry point starts the multi-process script
ENTRYPOINT ["/usr/local/bin/start_services.sh"]
