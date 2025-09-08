# syntax=docker/dockerfile:1
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Fly will set PORT; default to 8000 locally
ENV PORT=8000
EXPOSE 8000
CMD ["/bin/sh", "-c", "uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}"]
