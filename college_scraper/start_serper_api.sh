#!/bin/bash

echo "🚀 Starting Serper API Server..."
echo "📍 Port: 8500"
echo "📍 MongoDB: erdth database"
echo "📍 Collection: college_details"
echo "📍 Redis: localhost:6379"
echo ""

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Set environment variables
export MONGO_URI="mongodb://localhost:27017"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"

# Start the API server
echo "🌟 Starting FastAPI server on port 8500..."
python serper_api.py
