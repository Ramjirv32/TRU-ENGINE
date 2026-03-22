#!/bin/bash

# Simple run script - Start everything needed

echo "🎓 College Intelligence Platform - Quick Start"
echo "================================================"
echo ""

# Check if Redis is running
echo "Checking Redis..."
if ! redis-cli ping > /dev/null 2>&1; then
    echo "⚠️  Redis not running. Starting Redis..."
    redis-server --daemonize yes
    sleep 2
fi

if redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis: Running"
else
    echo "❌ Redis: Failed to start"
    echo "   Start manually: redis-server"
    exit 1
fi

echo ""
echo "Starting API Server..."
echo "================================================"
echo ""
echo "🌐 Server: http://localhost:5000"
echo "📚 Docs:   http://localhost:5000/api/health"
echo ""
echo "Press Ctrl+C to stop"
echo ""
cd /home/ramji/Videos/scap/college_scraper
python3 serper_redis.py server
