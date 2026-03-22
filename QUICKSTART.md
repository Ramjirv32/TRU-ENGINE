# 🚀 Quick Start Guide

Get the College Intelligence Platform running in 5 minutes!

## Prerequisites
- Python 3.8+ 
- Redis Server
- Modern web browser

## Installation & Launch (Choose One)

### ⚡ For Linux/Mac Users

```bash
# 1. Navigate to project
cd /home/ramji/Videos/scap

# 2. Run setup script (auto-installs everything)
chmod +x setup.sh
./setup.sh

# 3. Start Redis (in new terminal)
redis-server

# 4. Start API Server (in project directory)
cd college_scraper
python3 serper_redis.py server

# 5. Open browser
# Go to: http://localhost:5000
```

### 🪟 For Windows Users

```powershell
# 1. Navigate to project
cd C:\path\to\scap

# 2. Run setup script
setup.bat

# 3. Start Redis
redis-server
# OR use Docker: docker run -d -p 6379:6379 redis:latest

# 4. Start API Server
cd college_scraper
python serper_redis.py server

# 5. Open browser
# Go to: http://localhost:5000
```

### 🐳 Using Docker (Easiest)

```bash
# Start Redis in Docker
docker run -d -p 6379:6379 redis:latest

# Install Python dependencies
pip install -r requirements.txt

# Start server
cd college_scraper
python3 serper_redis.py server
```

## 🎯 First Search

1. Open http://localhost:5000 in browser
2. Type college name: `Udayana University`
3. Click **Search**
4. Explore tabs:
   - 📊 Overview - General info
   - 💼 Placements - Job stats
   - 💰 Fees - Cost breakdown
   - 🎯 Programs - All courses
   - 🏗️ Infrastructure - Campus facilities
   - 🏆 Rankings - Performance metrics

## ❓ Troubleshooting

### Error: "Cannot connect to Redis"
```bash
# Check if Redis is running
redis-cli ping
# Should return: PONG

# If not running:
redis-server  # Linux/Mac
# OR
docker run -d -p 6379:6379 redis:latest  # Docker
```

### Error: "Port 5000 already in use"
```bash
# Kill process on port 5000 (Linux/Mac)
lsof -ti:5000 | xargs kill -9

# Or use different port in serper_redis.py:
app.run(host='0.0.0.0', port=8080)
```

### Error: "Module flask not found"
```bash
pip install flask flask-cors
```

### Error: "Connection timeout when searching"
- Check internet connection
- Verify Serper API key is valid
- Increase timeout in code if needed
- Try a simpler search query

## 📊 What Each Tab Shows

| Tab | Shows | Example |
|-----|-------|---------|
| 📊 Overview | College info, accreditations | Est. year, institution type |
| 💼 Placements | Job stats, top recruiters | Avg package, placement rate |
| 💰 Fees | UG/PG costs, scholarships | Per-year fees, available aid |
| 🎯 Programs | All courses offered | UG/PG/PhD list, departments |
| 🏗️ Infrastructure | Campus facilities | Hostels, library, transport |
| 🏆 Rankings | Performance metrics | NIRF, QS, National, State |

## 🔍 Example Searches

Try these college names:
- `Udayana University` - Indonesian university
- `IIT Delhi` - Top Indian college
- `MIT` - US institution
- `Stanford University` - US university
- `University of Tokyo` - Japanese university

## ✨ Features

- ✅ **Instant Cache** - Searches cached after first fetch
- ✅ **White Theme** - Clean Material-UI design
- ✅ **Responsive** - Works on desktop, tablet, mobile
- ✅ **Real-time Data** - Uses Serper API for latest info
- ✅ **6 Data Tabs** - Comprehensive college info
- ✅ **Stat Cards** - Key metrics at a glance

## 📱 Using on Mobile

1. Find your computer's IP: `ipconfig` (Windows) or `ifconfig` (Linux/Mac)
2. On phone, go to: `http://YOUR_IP:5000`
3. Example: `http://192.168.1.100:5000`

## 🛑 Stopping the Server

Press `Ctrl + C` in the terminal running the API server

To stop Redis:
```bash
redis-cli shutdown  # Linux/Mac
# OR press Ctrl+C in Redis terminal
```

## 📞 Need Help?

1. Read [README.md](README.md) for detailed docs
2. Check [Troubleshooting](#-troubleshooting) section
3. Review [API Endpoints](README.md#-api-endpoints) for custom usage

---

**Ready?** Follow the installation steps above and search for your college! 🎓
