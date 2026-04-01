# Quick Reference Guide - Project Structure

## Folder Organization

```
scap/
├── college_scraper/           # Python data acquisition service
│   ├── serper_api.py         # FastAPI server with WebSocket
│   ├── serper.py             # Serper API integration, curl commands
│   ├── groq_college_validator.py
│   ├── normalizer.py         # Data schema mapping
│   ├── requirements.txt       # Python dependencies
│   └── docker-compose.yml     # MongoDB + Redis + PyAPI service
│
├── go-Engine/                # Main Go backend (Port 9000)
│   ├── main.go              # Entry point, service initialization
│   ├── go.mod               # Go module dependencies
│   │
│   ├── routes/              # HTTP route handlers
│   │   ├── routes.go        # Main router setup
│   │   ├── auth_routes.go
│   │   ├── college_routes.go
│   │   ├── assessment_routes.go
│   │   ├── admin/
│   │   └── college/college_routes.go
│   │
│   ├── controllers/         # Request handlers
│   │   ├── auth/*.go
│   │   ├── college/
│   │   ├── assessment/
│   │   │   ├── behavioral/
│   │   │   ├── cognitive/
│   │   │   ├── mbti/
│   │   │   ├── pescio/
│   │   │   ├── psychometric/
│   │   │   └── test/*.go
│   │   ├── admin/
│   │   ├── page/*.go
│   │   └── websocket/
│   │
│   ├── models/              # Database schema definitions
│   │   ├── college.go       # CollegeStats (100+ fields)
│   │   ├── user.go          # User & auth models
│   │   ├── psychometric.go
│   │   ├── mbti.go
│   │   ├── test.go
│   │   ├── cognitive.go
│   │   ├── pescio.go
│   │   └── profile.go
│   │
│   ├── services/            # Business logic & integrations
│   │   ├── ai/              # AI integrations
│   │   │   ├── serper_service.go    # Serper API + JSON schema
│   │   │   ├── groq_service.go      # Groq validation
│   │   │   ├── gemini_service.go
│   │   │   └── types.go
│   │   ├── auth/
│   │   ├── college/
│   │   ├── assessment/
│   │   ├── cache/           # Redis service
│   │   ├── messaging/       # RabbitMQ
│   │   ├── realtime/        # WebSocket management
│   │   └── brave/
│   │
│   ├── config/              # Configuration & connections
│   │   ├── database.go      # MongoDB setup
│   │   └── redis.go         # Redis/Dragonfly setup
│   │
│   ├── middleware/          # HTTP middleware
│   │   ├── auth.go          # JWT validation, role checks
│   │   └── cors.go
│   │
│   ├── utils/               # Utility functions
│   │   ├── response.go      # JSON response helpers
│   │   └── hash.go
│   │
│   ├── scripts/             # Utility scripts
│   ├── ok.env              # Environment variables
│   └── README.md           # Backend documentation
│
├── University/              # Main Frontend (Port 3000)
│   ├── package.json         # Dependencies: Next.js 16, React 19, Tailwind
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── postcss.config.mjs
│   │
│   ├── app/                # Next.js app router
│   │   ├── page.tsx        # Home page
│   │   ├── layout.tsx      # Root layout
│   │   ├── globals.css     # Global styles
│   │   │
│   │   ├── college-details/
│   │   │   └── [name]/
│   │   │       ├── page.tsx          # Main college details component
│   │   │       ├── styles.css
│   │   │       └── hooks.ts          # useCountUp, useInView
│   │   │
│   │   ├── user-dashboard/
│   │   │   ├── psychometric-result/
│   │   │   ├── test-results/
│   │   │   └── TestResultsClient.tsx
│   │   │
│   │   ├── admin/
│   │   │
│   │   └── api/            # Next.js API routes
│   │       ├── universities/route.ts     # College listing
│   │       └── dontsettle/route.ts       # Advanced filters
│   │
│   ├── components/         # Reusable React components
│   │   ├── home/
│   │   │   └── dontsettle/
│   │   │       └── UniversityList.tsx
│   │   ├── Certificate.tsx
│   │   └── ... (many more)
│   │
│   ├── contexts/           # React Context
│   │   └── AuthContext.tsx  # User auth state
│   │
│   ├── hooks/              # Custom React hooks
│   │   └── useAuth.ts
│   │
│   ├── lib/                # Utilities
│   │   ├── config.ts       # API URLs, endpoints
│   │   ├── mbtiDescriptions.ts
│   │   └── ... (helpers)
│   │
│   ├── public/             # Static assets
│   │   ├── images/
│   │   └── fonts/
│   │
│   └── README.md           # Frontend documentation
│
└── cougem/                 # Realtime/Testing Interface
    ├── package.json
    ├── index.html
    ├── realtime_test.html
    └── app/               # Next.js app
```

## Key Database Collections

### MongoDB (tru-main database)
```javascript
// College statistics - comprehensive document
college_details: {
  college_name, short_name, established, institution_type, country, location,
  rankings: {nirf_2025, nirf_2024, qs_world, ...},
  rankings_history: [{year, rank, source}],
  student_statistics_detail: {...},
  student_history: [{year: 2026, ug, pg, phd, ...}],
  faculty_staff_detail: {...},
  placements: {year, highest_pkg, avg_pkg, placement_rate, ...},
  placement_comparison_last_3_years: [{year, avg_pkg, rate}],
  fees: {UG: {per_year, total}, PG: {...}, PhD: {...}},
  fees_by_year: [{year, UG: {...}, ...}],
  scholarships_detail: [{name, amount, currency, eligibility}],
  infrastructure: [{facility, details}],
  approval_status: "pending" | "approved",
  created_at, updated_at, approved_by
}

// Users
users: {
  name, email, password (hashed), role ("user"|"admin"),
  date_of_birth, age, student_type, is_verified,
  created_at, updated_at, last_login
}

// Assessment results - one collection per test type
mvti_test_results, cognitive_test_results, etc: {
  user_id, email, name, test_type,
  answers: [{question_id, selected_option, is_correct, score}],
  total_score, max_score, percentage,
  interpretation, certificate_url, total_time_spent,
  completed_at, created_at
}

// Other
search_analytics: {user_id, query, results_count, timestamp}
test_sessions: {user_id, test_type, started_at, status}
student_profiles: {user_id, specializations, interests, ...}
```

## API Endpoint Cheat Sheet

### Authentication
```
POST   /api/auth/signup                  - Register
POST   /api/auth/login                   - Login
GET    /api/auth/verify-email?token=X   - Verify email
POST   /api/auth/resend-verification     - Resend verification
GET    /api/auth/me                      - Get current user (protected)
```

### College Data
```
GET    /api/college-statistics?college_name=X    - Full college info
GET    /api/all-colleges                         - All colleges (paginated)
GET    /api/search?university_name=X             - Search colleges
GET    /api/countries                            - List countries
GET    /api/colleges-by-country?country=X        - Filter by country
GET    /api/most-searched                        - Top searched colleges
POST   /api/college/validate                     - Validate college name
```

### Assessments (all protected)
```
POST   /api/psychometric/register                - Register for test
GET    /api/psychometric/registration            - Get registration status
GET    /api/psychometric/questions               - Fetch questions
POST   /api/psychometric/submit                  - Submit answers
GET    /api/psychometric/result                  - Get results

# Same pattern for: /mbti, /cognitive, /pescio, /behavioral
```

### Admin (protected + admin-only)
```
POST   /api/admin/college/*              - College management
POST   /api/admin/assessment/*           - Assessment management
POST   /api/admin/redis/*                - Cache control
GET    /api/admin/user/*                 - User management
```

### System
```
GET    /api/health                       - Health check
GET    /api/version                      - Version info
GET    /check/automate                   - Automation status
WS     /ws                               - WebSocket connection
```

## Configuration Files

### .env Variables
```
GEMINI_API_KEY              # Google Gemini API key
GROQ_API_KEY               # Groq API key for validation
MONGO_URI                  # MongoDB connection string
                          # Example: mongodb://192.168.14.50:27017/tru
PORT                       # Server port (default: 9000)
ENVIRONMENT                # "development" or "production"

REDIS_HOST                # Redis server hostname
REDIS_PORT                # Redis port (default: 6379)
REDIS_PASSWORD            # Redis password (if any)
REDIS_DB                  # Redis database number

SMTP_HOST                 # Email SMTP server
SMTP_PORT                 # SMTP port (usually 587)
SMTP_EMAIL                # From email address
SMTP_PASSWORD             # SMTP password

ADMIN_EMAIL               # Initial admin user email
ADMIN_PASSWORD            # Initial admin password
JWT_SECRET                # Secret for JWT token signing

RABBITMQ_URL              # RabbitMQ connection string
RABBITMQ_EXCHANGE         # RabbitMQ exchange name
RABBITMQ_QUEUE            # RabbitMQ queue name
```

### docker-compose.yml Services
```yaml
mongodb:6.0          - Port 27017, volume: mongodb_data
redis:7              - Port 6379 (Dragonfly compatible)
college-scraper      - Port 8501 (Python FastAPI)
```

## Important Dependencies by Language

### Go (go.mod)
```
github.com/gorilla/mux              - HTTP router
github.com/gorilla/websocket        - WebSocket support
go.mongodb.org/mongo-driver         - MongoDB client
github.com/go-redis/redis/v8        - Redis client
github.com/rabbitmq/amqp091-go      - RabbitMQ client
github.com/golang-jwt/jwt/v5        - JWT handling
golang.org/x/crypto                 - Password hashing
gopkg.in/gomail.v2                  - Email sending
github.com/joho/godotenv            - .env file loading
```

### Python (requirements.txt)
```
fastapi==0.104.1            - Web framework
uvicorn[standard]==0.24.0  - ASGI server
pydantic==2.5.0            - Data validation
pymongo==4.6.0             - MongoDB driver
redis==5.0.1               - Redis client
websockets==12.0           - WebSocket support
requests==2.31.0           - HTTP client
python-dotenv==1.0.0       - .env loading
```

### Frontend (package.json)
```
next: 16.1.1                - React framework
react: 19.2.0
react-dom: 19.2.0
tailwindcss: 3.4.15         - CSS utility framework
typescript: 5               - Type checking
axios: 1.13.2               - HTTP client
chart.js: 4.5.1             - Charts
lucide-react: 0.553.0       - Icons
jspdf: 3.0.4                - PDF generation
html2canvas: 1.4.1          - Screenshot to image
```

## Testing a Component Locally

### Start MongoDB + Redis (via docker-compose)
```bash
cd college_scraper
docker-compose up -d
```

### Start Go Backend
```bash
cd go-Engine
go run main.go
# Runs on http://localhost:9000
```

### Start Python API
```bash
cd college_scraper
python -m uvicorn serper_api:app --host 0.0.0.0 --port 8501
# Runs on http://localhost:8501
```

### Start Next.js Frontend
```bash
cd University
npm dev
# Runs on http://localhost:3000
```

## Common Debug Points

1. **College data not appearing**
   - Check MongoDB connection: `mongosh mongodb://localhost:27017/tru`
   - Check Redis cache: `redis-cli ping`
   - Check Go backend logs for connection errors

2. **Assessment not scoring**
   - Verify MongoDB has test collections
   - Check Redis has question cache
   - Verify admin approval in database

3. **WebSocket not updating**
   - Check RabbitMQ connection in Go backend
   - Verify WebSocket route: `/ws`
   - Check browser console for WebSocket errors

4. **College scraping fails**
   - Verify Serper API key valid: `ok.env`
   - Check Groq API key: `ok.env`
   - Verify Python API running on http://localhost:8501
   - Check MongoDB write permissions

## Performance Notes

- College data cached for 1 hour in Redis
- Assessment questions cached per test type
- Search results paginated (10 results per page)
- WebSocket keeps 1 connection per client
- RabbitMQ consumes cache invalidation events asynchronously

## Scaling Considerations

- **Horizontal**: Can scale Go backend with load balancer
- **Database**: MongoDB replica set for high availability
- **Cache**: Redis cluster for distributed caching
- **Queue**: RabbitMQ cluster for message distribution
- **Frontend**: Static build deployment to CDN
