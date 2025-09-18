# syntax=docker/dockerfile:1
FROM node:18-bullseye AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

# Install Python + system deps for audio processing and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    build-essential \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# ---------------------------
# Backend (FastAPI)
# ---------------------------
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy entire repo (backend code lives at project root with main.py)
COPY . .

# ---------------------------
# Frontend (Next.js)
# ---------------------------
WORKDIR /app/frontend-nextjs
COPY frontend-nextjs/package*.json ./
RUN npm install
# Copy the rest of the frontend
COPY frontend-nextjs/ /app/frontend-nextjs/

# ---------------------------
# Process Manager
# ---------------------------
WORKDIR /app
RUN npm install -g concurrently

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash sophia && \
    chown -R sophia:sophia /app
USER sophia

# Health check (backend only)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8000/health')"

# Fly will set PORT; default to 8000 locally
ENV PORT=8000
EXPOSE 8000

# Start both processes: FastAPI on 8000 (exposed) and Next.js dev server on 3000 (internal)
CMD ["sh", "-c", "concurrently \"uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}\" \"npm --prefix frontend-nextjs run dev -- -p 3000\""]
