@echo off
REM Simple run script - Start everything needed

echo.
echo College Intelligence Platform - Quick Start
echo ================================================
echo.

REM Check if Redis is running
echo Checking Redis...
(redis-cli ping > nul 2>&1) && (
    echo ✓ Redis: Running
) || (
    echo Redis not running. Make sure it's started first:
    echo   redis-server
    echo or
    echo   docker run -d -p 6379:6379 redis:latest
    pause
    exit /b 1
)

echo.
echo Starting API Server...
echo ================================================
echo.
echo Browser: http://localhost:5000
echo Press Ctrl+C to stop
echo.

cd /home/ramji/Videos/scap/college_scraper
python serper_redis.py server
pause
