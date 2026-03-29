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
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project files
COPY . .

# Pre-download the local embedding model during build (avoids runtime timeout)
RUN python3 -c "from fastembed import TextEmbedding; TextEmbedding(model_name='BAAI/bge-small-en-v1.5')"

# Create directories for persistent data if they don't exist
RUN mkdir -p data/sync/incoming data/sync/archive faiss_index

# Copy the start script and make it executable
COPY start_services.sh /usr/local/bin/start_services.sh
RUN chmod +x /usr/local/bin/start_services.sh

# Expose the single ingress port (Hugging Face default)
EXPOSE 7860

# Entry point starts the multi-process script
ENTRYPOINT ["/usr/local/bin/start_services.sh"]
