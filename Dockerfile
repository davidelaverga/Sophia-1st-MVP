# Backend-Only Dockerfile for Render Deployment
# Frontend is deployed separately on Vercel

FROM python:3.10-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install system dependencies for audio processing
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code only (no frontend)
COPY main.py ./
COPY app/ ./app/

# Copy SQL files if they exist
COPY *.sql ./

# Copy grafana-dashboards directory if it exists
COPY grafana-dashboards/ ./grafana-dashboards/

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash sophia && \
    chown -R sophia:sophia /app
USER sophia

# Health check for backend
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${PORT:-8000}/health || exit 1

# Use PORT environment variable (Render sets this)
ENV PORT=8000
EXPOSE $PORT

# Start only the FastAPI backend
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}
