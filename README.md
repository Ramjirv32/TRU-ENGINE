# 📚 College Intelligence Platform

A modern, interactive college information platform with Material-UI based frontend and Python/Serper API backend.

## 🎯 Features

### Frontend (index.html)
- **Modern White Theme** - Clean Material-UI design with gradient accents
- **College Search** - Search by college name  
- **Interactive Dashboards** - Six comprehensive tabs:
  - 📊 Overview - College summary and accreditations
  - 💼 Placements - Placement statistics, top recruiters
  - 💰 Fees - Fee structure and scholarships
  - 🎯 Programs - All UG, PG, PhD programs & departments
  - 🏗️ Infrastructure - Hostels, library, facilities
  - 🏆 Rankings - NIRF, QS, National, and State rankings

- **Key Metrics** - Animated stat cards with:
  - Student enrollment & demographics
  - Gender ratio tracking
  - Faculty statistics
  - Program counts

- **Responsive Design** - Works on desktop, tablet, and mobile
- **Data Caching** - Results cached in Redis for fast retrieval

### Backend (serper_redis.py)
- **Serper API Integration** - Fetch college data from Google AI Mode
- **Redis Caching** - Store and retrieve cached data
- **Parallel Processing** - Concurrent data fetching (5 async workers)
- **Flask API Server** - RESTful API endpoints
- **Auto JSON Extraction** - Intelligent markdown to JSON conversion

## 🛠️ Installation

### Prerequisites
- Python 3.8+
- Redis Server (running)
- pip

### Step 1: Install Dependencies
```bash
cd /home/ramji/Videos/scap
pip install -r requirements.txt
```

### Step 2: Start Redis Server
```bash
# On Linux/Mac
redis-server

# On Windows
redis-server.exe

# Or if using Docker
docker run -d -p 6379:6379 redis:latest
```

### Step 3: Verify Redis Connection
```bash
redis-cli ping
# Should return: PONG
```

## 🚀 Running the Application

### Option 1: Run as Web Server (Recommended)
```bash
cd /home/ramji/Videos/scap/college_scraper
python serper_redis.py server
```

Then open in browser:
```
http://localhost:5000
```

### Option 2: Run as CLI (Batch Processing)
```bash
cd /home/ramji/Videos/scap/college_scraper
python serper_redis.py
```

This fetches data for all colleges in COLLEGES list and saves to `serper_results.json`

### Option 3: Serve HTML Locally
```bash
cd /home/ramji/Videos/scap
python -m http.server 8000
```

Then visit:
```
http://localhost:8000/index.html
```

Note: Requires backend API running separately on port 5000

## 📡 API Endpoints

### Health Check
```
GET /api/health
```
Response:
```json
{
  "status": "healthy",
  "message": "College Intelligence API is running"
}
```

### Search College
```
POST /api/college
Content-Type: application/json

{
  "college_name": "Udayana University"
}
```

Response:
```json
{
  "basic_info": { ... },
  "placements": { ... },
  "fees": { ... },
  "programs": { ... },
  "infrastructure": { ... },
  "_metadata": {
    "total_time": 45.32,
    "errors": {},
    "source": "fresh" | "cache"
  }
}
```

### Get Available Colleges
```
GET /api/colleges-list
```

## 📊 Data Structure

### Basic Info
```json
{
  "college_name": "string",
  "established": "year",
  "institution_type": "string",
  "country": "string",
  "location": "string",
  "website": "url",
  "rankings": {
    "nirf_rank": "number or -1",
    "qs_world": "number",  
    "national_rank": "number",
    "state_rank": "number"
  },
  "student_statistics": {
    "total_enrollment": "number",
    "ug_students": "number",
    "pg_students": "number",
    "female_percent": "number",
    "total_faculty": "number",
    "student_faculty_ratio": "number"
  }
}
```

### Placements
```json
{
  "placements": {
    "highest_package": "number",
    "average_package": "number",
    "placement_rate_percent": "number",
    "total_students_placed": "number",
    "total_companies_visited": "number"
  },
  "top_recruiters": ["company1", "company2", ...],
  "sector_wise_placement_last_3_years": [...]
}
```

### Fees
```json
{
  "fees": {
    "UG": {
      "per_year": "number",
      "total_course": "number",
      "currency": "INR"
    },
    "PG": { ... }
  },
  "scholarships_detail": [
    {
      "name": "string",
      "amount": "number",
      "eligibility": "string"
    }
  ]
}
```

## 🔧 Configuration

Edit `/home/ramji/Videos/scap/college_scraper/serper_redis.py`:

```python
# Change API Key
API_KEY = "your-serper-api-key"

# Add more colleges to track
COLLEGES = [
    {"name": "College Name", "country": "Country", "location": "City"},
]

# Adjust parallel workers
ThreadPoolExecutor(max_workers=5)  # Change 5 to desired number

# Change Redis connection
redis.Redis(host='localhost', port=6379, db=0)
```

## 🎨 Customization

### Color Scheme (in index.html)
- Primary Blue: `#1976d2`
- Success Green: `#388e3c`
- Warning Orange: `#f57c00`
- Error Red: `#d32f2f`
- Purple: `#7b1fa2`

Edit colors in `<style>` section

### Add Custom Metrics
Modify `renderStatsSection()` in the JavaScript to add new stat cards

### Customize Tab Data
Edit `renderTabContent()` and tab-specific render methods

## 🐛 Troubleshooting

### Redis Connection Error
```
redis.exceptions.ConnectionError: Error 111 connecting to localhost:6379
```
**Solution:** Start Redis server
```bash
redis-server
```

### Flask Not Found
```
ModuleNotFoundError: No module named 'flask'
```
**Solution:** Install requirements
```bash
pip install -r requirements.txt
```

### Port Already in Use
```
OSError: [Errno 48] Address already in use
```
**Solution:** Change port in serper_redis.py
```python
app.run(host='0.0.0.0', port=8080)  # Use 8080 instead
```

### Serper API Rate Limit
**Solution:** Reduce number of parallel workers or add delay
```python
# In serper_redis.py
ThreadPoolExecutor(max_workers=2)  # Reduce from 5 to 2
time.sleep(1)  # Add delay between requests
```

## 📈 Performance Tips

1. **Caching** - First search takes ~45 seconds, cached results return instantly
2. **Parallel Processing** - Data fetched concurrently (5 workers by default)
3. **Compression** - Results compressed in Redis for faster retrieval
4. **Lazy Loading** - Tab content rendered on-demand

## 🔒 Security

- CORS enabled for cross-origin requests
- No sensitive data in client-side code
- Redis should be on secure network
- Use environment variables for API keys (optional enhancement)

## 📝 Future Enhancements

- [ ] University comparison (multiple colleges)
- [ ] Historical data tracking
- [ ] User favorites/bookmarks
- [ ] Advanced filtering (fees range, location, etc.)
- [ ] PDF export functionality
- [ ] Dark mode theme
- [ ] Mobile app version
- [ ] Email notifications for updates

## 📞 Support

For issues or questions:
1. Check Redis is running: `redis-cli ping`
2. Verify API key is valid
3. Check network connectivity to serper.dev
4. Review logs in terminal

## 📄 License

MIT License - Feel free to use and modify

---

Built with ❤️ using Material-UI, Recharts, and Flask
