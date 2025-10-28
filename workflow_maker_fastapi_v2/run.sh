#!/bin/bash

# Workflow Maker FastAPI - Startup Script
# This script starts the workflow builder AI service

set -e

echo "🚀 Starting Workflow Maker FastAPI Service..."

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  Warning: .env file not found. Using default configuration."
    echo "💡 Tip: Copy .env.example to .env and configure your GOOGLE_API_KEY"
fi

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Default values if not set
export HOST=${HOST:-0.0.0.0}
export PORT=${PORT:-8002}
export DB_PATH=${DB_PATH:-messages.db}

# Check for Google API key
if [ -z "$GOOGLE_API_KEY" ]; then
    echo "❌ Error: GOOGLE_API_KEY not set"
    echo "Please set your Google API key in the .env file"
    exit 1
fi

echo "✅ Configuration loaded:"
echo "   - Host: $HOST"
echo "   - Port: $PORT"
echo "   - Database: $DB_PATH"
echo "   - Model: ${MODEL_NAME:-gemini-1.5-flash-latest}"
echo ""
echo "📡 Service will be available at: http://$HOST:$PORT"
echo "🏥 Health check: http://$HOST:$PORT/healthz"
echo ""

# Start uvicorn server
uvicorn app:app --host "$HOST" --port "$PORT" --reload
