#!/bin/bash

# College Intelligence Platform - Setup Script
# Run this script to set up the entire application

set -e  # Exit on error

echo "🎓 College Intelligence Platform Setup"
echo "======================================"
echo ""

# Color codes
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Step 1: Check Python
echo -e "${BLUE}Step 1: Checking Python installation...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${YELLOW}Python3 not found. Please install Python 3.8+${NC}"
    exit 1
fi
PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo -e "${GREEN}✓ Python $PYTHON_VERSION found${NC}"
echo ""

# Step 2: Check Redis
echo -e "${BLUE}Step 2: Checking Redis installation...${NC}"
if ! command -v redis-cli &> /dev/null; then
    echo -e "${YELLOW}Redis not found. Installing Redis...${NC}"
    if [[ "$OSTYPE" == "linux-gnu"* ]]; then
        sudo apt-get update
        sudo apt-get install -y redis-server
    elif [[ "$OSTYPE" == "darwin"* ]]; then
        brew install redis
    else
        echo -e "${YELLOW}Please install Redis manually from https://redis.io/download${NC}"
    fi
fi
echo -e "${GREEN}✓ Redis found${NC}"
echo ""

# Step 3: Install Python dependencies
echo -e "${BLUE}Step 3: Installing Python dependencies...${NC}"
python3 -m pip install --upgrade pip
python3 -m pip install -r requirements.txt
echo -e "${GREEN}✓ Dependencies installed${NC}"
echo ""

# Step 4: Test Redis connection
echo -e "${BLUE}Step 4: Testing Redis connection...${NC}"
if redis-cli ping > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Redis is running${NC}"
else
    echo -e "${YELLOW}Redis is not running. Start it with: redis-server${NC}"
fi
echo ""

# Step 5: Check file structure
echo -e "${BLUE}Step 5: Verifying file structure...${NC}"
if [ -f "index.html" ] && [ -f "college_scraper/serper_redis.py" ] && [ -f "requirements.txt" ]; then
    echo -e "${GREEN}✓ All required files found${NC}"
else
    echo -e "${YELLOW}Some files are missing${NC}"
fi
echo ""

# Step 6: Success message
echo -e "${GREEN}======================================"
echo "Setup Complete! ✓"
echo "=====================================${NC}"
echo ""
echo "Next steps:"
echo ""
echo "1. Start Redis (if not running):"
echo -e "   ${BLUE}redis-server${NC}"
echo ""
echo "2. Run the API server:"
echo -e "   ${BLUE}cd college_scraper${NC}"
echo -e "   ${BLUE}python3 serper_redis.py server${NC}"
echo ""
echo "3. Open in browser:"
echo -e "   ${BLUE}http://localhost:5000${NC}"
echo ""
echo "For more information, see README.md"
echo ""
