#!/bin/bash

# Load environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
fi

# Check if running from the correct directory
if [ ! -f "app.py" ]; then
    echo "Error: app.py not found. Make sure you're in the agent_maker_fastapi directory."
    exit 1
fi

# Check if virtual environment exists in parent directory
if [ ! -d "../.venv" ]; then
    echo "Error: Virtual environment not found at ../.venv"
    echo "Please create a virtual environment in the parent directory first."
    exit 1
fi

# Activate virtual environment
source ../.venv/bin/activate

# Install dependencies if needed
echo "Installing dependencies..."
cd .. && uv sync && cd agent_maker_fastapi

# Run the FastAPI application
echo "Starting FastAPI application..."
uvicorn app:app --host ${HOST:-0.0.0.0} --port ${PORT:-8001} --reload