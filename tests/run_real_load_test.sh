#!/bin/bash

# Real Load Testing Runner Script
# Runs actual WebSocket integration tests against running server

set -e

echo "╔═══════════════════════════════════════════════════════════╗"
echo "║     REAL WebSocket Integration Load Testing              ║"
echo "╚═══════════════════════════════════════════════════════════╝"
echo ""

# Configuration
SERVER_URL=${SERVER_URL:-"http://localhost:8000"}
WS_URL=${WS_URL:-"ws://localhost:8000"}
NUM_SESSIONS=${NUM_SESSIONS:-5}

echo "📋 Configuration:"
echo "   Server URL: $SERVER_URL"
echo "   WebSocket URL: $WS_URL"
echo "   Parallel sessions: $NUM_SESSIONS"
echo ""

# Check if server is running
echo "🔍 Checking if server is running..."
if curl -f -s "$SERVER_URL/health" > /dev/null 2>&1; then
    echo "✅ Server is running at $SERVER_URL"
else
    echo "❌ Server is not running at $SERVER_URL"
    echo ""
    echo "Please start the server first:"
    echo "   Option 1 (Local): uv run python main.py"
    echo "   Option 2 (Docker): docker-compose up"
    echo "   Option 3 (OrbStack): Start container in OrbStack"
    echo ""
    exit 1
fi

echo ""
echo "🚀 Starting REAL load tests..."
echo ""

# Run the real integration tests
python tests/test_real_websocket_integration.py

echo ""
echo "✅ Load tests completed!"
