@echo off
REM College Intelligence Platform - Windows Setup Script

setlocal enabledelayedexpansion

echo.
echo ====================================== 
echo College Intelligence Platform Setup
echo ======================================
echo.

REM Step 1: Check Python
echo [Step 1] Checking Python installation...
python --version > nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Please install Python 3.8+
    echo Download from: https://www.python.org/downloads/
    pause
    exit /b 1
)
python --version
echo.

REM Step 2: Check Redis  
echo [Step 2] Checking Redis installation...
where redis-cli > nul 2>&1
if errorlevel 1 (
    echo WARNING: Redis not found locally
    echo.
    echo Options:
    echo 1. Install Redis from: https://github.com/microsoftarchive/redis/releases
    echo 2. Use Docker: docker run -d -p 6379:6379 redis:latest
    echo 3. Use WSL: wsl redis-server
    echo.
    set /p redis_choice="Use Docker Redis? (y/n): "
    if /i "!redis_choice!"=="y" (
        docker run -d -p 6379:6379 redis:latest
        echo Docker Redis started
    ) else (
        echo Please install Redis before continuing
        pause
        exit /b 1
    )
) else (
    echo Redis found
)
echo.

REM Step 3: Install dependencies
echo [Step 3] Installing Python dependencies...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERROR: Failed to install dependencies
    pause
    exit /b 1
)
echo Dependencies installed successfully
echo.

REM Step 4: Create virtualenv (optional)
set /p venv_choice="Create Python virtual environment? (y/n): "
if /i "!venv_choice!"=="y" (
    python -m venv venv
    call venv\Scripts\activate.bat
    python -m pip install -r requirements.txt
    echo Virtual environment created and activated
)
echo.

REM Step 5: Success
echo ======================================
echo Setup Complete!
echo ======================================
echo.
echo Next steps:
echo.
echo 1. Start Redis (if not using Docker)
echo.
echo 2. Run the API server:
echo    cd college_scraper
echo    python serper_redis.py server
echo.
echo 3. Open browser:
echo    http://localhost:5000
echo.
echo For more info, read README.md
echo.
pause
