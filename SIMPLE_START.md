# 🚀 Simple Start Guide

Just 2 steps to get running!

## Step 1: Start Redis

### Linux/Mac
```bash
redis-server
```

### Windows
Download from: https://github.com/microsoftarchive/redis/releases

OR use Docker:
```bash
docker run -d -p 6379:6379 redis:latest
```

## Step 2: Run the Server

### Linux/Mac
```bash
cd /home/ramji/Videos/scap
chmod +x run.sh
./run.sh
```

### Windows
```powershell
cd C:\path\to\scap
run.bat
```

## Step 3: Open Browser

```
http://localhost:5000
```

Search for any college name and explore! ✓

---

## What's Happening?

1. **Redis** - Caches college data
2. **Python Server** - Fetches data from Serper API
3. **Browser** - Shows results in nice interface

---

## Troubleshooting

### "Redis Connection Error"
→ Start Redis first (see Step 1)

### "Port 5000 already in use"
→ Stop other server or change port in `serper_redis.py`

### "Module not found"
→ Install dependencies:
```bash
pip install -r requirements.txt
```

---

That's it! 🎉
