# Serper College Scraper API

A standalone FastAPI backend for college data scraping using Serper API, with Redis caching and MongoDB storage.

## Features

- **College Search**: Real-time college data scraping via Serper API
- **Data Storage**: MongoDB integration (same database as go-Engine)
- **Caching**: Redis caching for improved performance
- **WebSocket Support**: Real-time updates for frontend
- **Normalization**: Built-in data normalization and validation
- **RESTful API**: Clean REST endpoints for frontend integration

## Architecture

```
Frontend (Next.js) → Serper API (FastAPI) → MongoDB + Redis
                     ↓
              Serper Web Scraping
```

## Database Configuration

Uses the same database as go-Engine:
- **Database**: `erdth`
- **Collection**: `college_details`
- **Redis**: For caching college data

## API Endpoints

### Core Endpoints
- `GET /` - API info
- `GET /health` - Health check
- `GET /api/countries` - Get countries list
- `GET /api/colleges-by-country?country={name}` - Get colleges by country
- `POST /api/college-statistics` - Search/get college data (triggers scraping)
- `GET /api/most-searched?limit={n}` - Get most searched colleges

### WebSocket Endpoints
- `WS /ws/countries` - Real-time country updates
- `WS /ws/colleges` - Real-time college updates

## Setup Instructions

### 1. Install Dependencies
```bash
cd /home/ramji/Videos/scap/college_scraper
chmod +x start_serper_api.sh
./start_serper_api.sh
```

### 2. Manual Setup (Alternative)
```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MONGO_URI="mongodb://localhost:27017"
export REDIS_HOST="localhost"
export REDIS_PORT="6379"

# Start the server
python serper_api.py
```

### 3. Frontend Configuration
The frontend is already configured to use the serper API:
- Environment variable: `NEXT_PUBLIC_SERPER_API_URL=http://localhost:8500`
- Configuration in: `lib/config.ts`

## Usage Flow

### 1. College Search
```typescript
// Frontend calls
POST http://localhost:8500/api/college-statistics
{
  "college_name": "Anna University",
  "country": "India",
  "city": "Chennai"
}
```

### 2. API Response Flow
1. Check Redis cache
2. Check MongoDB database
3. If not found, trigger scraping with serper.py
4. Normalize data with normalizer.py
5. Save to MongoDB and cache in Redis
6. Return data to frontend

### 3. Real-time Updates
- WebSocket connections for live data updates
- Frontend receives updates during scraping process
- Chart updates in real-time as data becomes available

## File Structure

```
college_scraper/
├── serper_api.py              # FastAPI backend
├── serper.py                  # Main scraper (updated with normalizer)
├── normalizer.py              # Data normalization
├── requirements.txt           # Python dependencies
├── start_serper_api.sh       # Startup script
└── README_SERPER_API.md      # This file
```

## Integration with Frontend

### PieChartSection.tsx
- Fetches countries from `/api/countries`
- Fetches colleges by country from `/api/colleges-by-country`
- WebSocket connections for real-time updates
- Displays college statistics in interactive pie chart

### SearchModal.tsx
- College search via `/api/college-statistics`
- Shows most searched colleges from `/api/most-searched`
- Location-based filtering (country/city)
- Real-time search progress indicators

## Data Flow

1. **User searches** → Frontend calls serper API
2. **API checks cache** → Redis → MongoDB → Scraping
3. **Scraping process** → Serper API → Normalization → Storage
4. **Real-time updates** → WebSocket → Frontend chart updates
5. **Cached results** → Future requests served from cache

## Environment Variables

```bash
MONGO_URI="mongodb://localhost:27017"
REDIS_HOST="localhost"
REDIS_PORT="6379"
REDIS_PASSWORD=""  # Optional
```

## Running on Port 8500

The API is configured to run on port 8500 to avoid conflicts with:
- Go Engine (port 9000)
- Frontend (port 3000)

## Testing the API

```bash
# Health check
curl http://localhost:8500/health

# Get countries
curl http://localhost:8500/api/countries

# Search college
curl -X POST http://localhost:8500/api/college-statistics \
  -H "Content-Type: application/json" \
  -d '{"college_name": "Anna University", "country": "India"}'
```

## Benefits

1. **Standalone Service**: Independent of go-Engine for college data
2. **Real-time Updates**: WebSocket support for live scraping updates
3. **Performance**: Redis caching for fast responses
4. **Data Quality**: Built-in normalization and validation
5. **Scalability**: FastAPI async support for high concurrency
6. **Integration**: Seamless frontend integration with existing components

## Troubleshooting

### Common Issues
1. **Port 8500 in use**: Change port in serper_api.py
2. **MongoDB connection**: Check MONGO_URI environment variable
3. **Redis connection**: Verify Redis is running on localhost:6379
4. **Serper API key**: Update API_KEY in serper.py

### Logs
The API provides detailed logging for:
- Database connections
- Scraping progress
- Cache hits/misses
- WebSocket connections
- Error details

## Future Enhancements

1. **Authentication**: Add API key authentication
2. **Rate Limiting**: Implement rate limiting for scraping
3. **Batch Processing**: Support for multiple college scraping
4. **Analytics**: Track search patterns and popular colleges
5. **Monitoring**: Add health checks and metrics
