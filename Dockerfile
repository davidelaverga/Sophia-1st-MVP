# syntax=docker/dockerfile:1

# ---------------------------
# Stage 1: Build Next.js (standalone)
# ---------------------------
FROM node:18-alpine AS frontend-builder
WORKDIR /app/frontend-nextjs
COPY frontend-nextjs/package*.json ./
RUN npm ci
COPY frontend-nextjs/ ./
# Build Next.js with standalone output
RUN npm run build

# ---------------------------
# Stage 2: Final runtime (Node + Python slim)
# ---------------------------
FROM node:18-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app

WORKDIR /app

# Install Python + minimal system deps needed for audio
RUN apt-get update && apt-get install -y --no-install-recommends \
    python3 python3-pip python3-venv \
    ffmpeg \
    libsndfile1 \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies first to leverage layer caching
COPY requirements.txt ./
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy backend code (root contains main.py and app/)
COPY . .

# Copy only the minimal Next.js standalone artifacts to keep image small
# - standalone server
# - static assets
# - public assets
RUN mkdir -p /opt/next
COPY --from=frontend-builder /app/frontend-nextjs/.next/standalone /opt/next/
COPY --from=frontend-builder /app/frontend-nextjs/.next/static /opt/next/.next/static
COPY --from=frontend-builder /app/frontend-nextjs/public /opt/next/public

# Install a small process manager
RUN npm install -g concurrently

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash sophia && \
    chown -R sophia:sophia /app /opt/next
USER sophia

# Health check (backend only)
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://localhost:8000/health')"

# Fly will set PORT; default to 8000 locally
ENV PORT=8000
EXPOSE 8000

# Start both processes:
# - FastAPI on 8000 (exposed)
# - Next.js standalone server on 3000 (internal)
CMD ["sh", "-c", "concurrently \"uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}\" \"sh -lc 'cd /opt/next && node server.js -p 3000 -H 0.0.0.0'\""]
