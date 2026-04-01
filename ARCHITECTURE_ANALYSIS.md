# Project Architecture Analysis - College Recommendation & Assessment Platform

## 1. Overall Architecture

### System Components Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                     CLIENT LAYER (Frontends)                        │
├──────────────────────────┬──────────────────────┬───────────────────┤
│  University              │  Cougem              │  Admin/Internal  │
│  (Next.js 16.1.1)        │  (Next.js)           │  Components      │
│  - College Search        │  - College Details   │                  │
│  - Assessments UI        │  - Realtime Testing  │                  │
│  - Results Dashboard     │  - Live Results      │                  │
│  - User Authentication   │                      │                  │
└──────────────────────────┴──────────────────────┴───────────────────┘
                                  ↕ (HTTP/WebSocket)
┌─────────────────────────────────────────────────────────────────────┐
│                        API GATEWAY LAYER                            │
│                   Go Backend (main.go - Port 9000)                  │
├─────────────────────────────────────────────────────────────────────┤
│                        Gorilla Mux Router                           │
│    ├─ CORS Middleware     ├─ Auth Middleware   ├─ Admin Check     │
│    └─ Health Checks       ├─ JWT Validation    └─ Role-based      │
└─────────────────────────────────────────────────────────────────────┘
                ↕                           ↕                    ↕
        ┌───────────────┐      ┌────────────────────┐    ┌──────────────┐
        │  Routes       │      │   Services Layer   │    │   External   │
        ├───────────────┤      ├────────────────────┤    │   Services   │
        │ - Auth        │      │ - College Service  │    ├──────────────┤
        │ - College     │      │ - Assessment Svc   │    │ - Serper API │
        │ - Assessment  │      │ - Auth Service     │    │   (Search)   │
        │ - Admin       │      │ - Redis Cache      │    │ - Groq API   │
        │ - WebSocket   │      │ - RabbitMQ Queue   │    │   (Validate) │
        └───────────────┘      │ - AI Services      │    │ - Gemini     │
                               │   (Gemini/Groq)    │    │   (AI)       │
                               └────────────────────┘    └──────────────┘
                                         ↕
        ┌─────────────────────────────────────────────────────┐
        │           Data & Cache Layer                        │
        ├──────────────────────┬──────────────────────────────┤
        │  MongoDB             │  Redis/Dragonfly Cache       │
        │  (Database)          │  (Session & Query Cache)     │
        │  - College Details   │  - Test Questions            │
        │  - User Profiles     │  - Assessment Sessions       │
        │  - Assessment Results│  - Search Analytics          │
        │  - Placements Data   │  (1-hour TTL)                │
        └──────────────────────┴──────────────────────────────┘
                                         ↕
        ┌─────────────────────────────────────────────────────┐
        │           Message Queue & Realtime                  │
        ├──────────────────────┬──────────────────────────────┤
        │  RabbitMQ            │  WebSocket (Gorilla)         │
        │  - Event Broadcasting│  - Live Test Updates         │
        │  - Cache Invalidation│  - Real-time Results         │
        │  - Async Processing  │  - Admin Notifications       │
        └──────────────────────┴──────────────────────────────┘
                                         ↕
        ┌─────────────────────────────────────────────────────┐
        │        Data Acquisition & Processing                │
        ├─────────────────────────────────────────────────────┤
        │  Python API (FastAPI - college_scraper)             │
        │  - Serper Search Integration                        │
        │  - College Data Normalization                       │
        │  - Groq Validation                                  │
        │  - WebSocket Real-time Status                       │
        └─────────────────────────────────────────────────────┘
```

## 2. Core Components

### 2.1 Frontend Applications

#### **University (Port 3000)**
- **Framework**: Next.js 16.1.1 with TypeScript
- **Key Features**:
  - College search and filtering
  - Detailed college information pages (`/college-details/[name]`)
  - User authentication and dashboard
  - Multiple assessment systems (Psychometric, MBTI, Cognitive, PESCIO, Behavioral)
  - Test results visualization with charts
  - Responsive design with Tailwind CSS
- **Key Dependencies**: React 19.2.0, Chart.js, Zingchart, Lucide-react
- **API Integration**: Communicates with Go backend via REST + WebSocket

#### **Cougem**
- **Framework**: Next.js
- **Purpose**: Real-time college details and testing interface
- **Key Features**:
  - Live college statistics display
  - Real-time test tracking
  - HTML-based realtime updates (`realtime_test.html`)

### 2.2 Backend Services

#### **Go Backend (Port 9000)**
- **Language**: Go 1.24.0
- **Framework**: Gorilla Mux (HTTP routing)
- **Core Entry**: `main.go`

**Initialization Sequence**:
1. Load `.env` variables
2. Initialize Cache Service (1-hour TTL)
3. Connect to MongoDB (database "tru-main")
4. Connect to Redis (optional, falls back gracefully)
5. Initialize RabbitMQ for event broadcasting
6. Create default admin user
7. Setup routes and start HTTP server on Port 9000

**Database Collections**:
```
MongoDB (tru-main)
├── college_details              # Complete college information
├── users                        # User accounts & auth
├── search_analytics             # Search tracking
├── minor_students               # Student classifications
├── major_students
├── mvti_test_results            # MVTI test data
├── cognitive_test_results       # Cognitive assessment data
├── test_sessions                # Test session tracking
└── student_profiles             # User profile data
```

#### **Python API (college_scraper, Port 8501)**
- **Framework**: FastAPI 0.104.1
- **Purpose**: Data acquisition and normalization
- **Key File**: `serper_api.py`

**Features**:
- WebSocket support for real-time scraping updates
- Serper API integration for college searches
- College data normalization and formatting
- Groq-based college name validation
- MongoDB integration for data persistence
- Redis caching for optimization

**Query Categories**:
```python
QUERIES = {
    "basic_info": Basic college info + rankings + student statistics
    "ug_programs": Undergraduate programs
    "pg_programs": Postgraduate programs  
    "phd_programs": Doctoral programs
    "departments": Academic departments
    "placements": Placement statistics (3-year history)
    "fees": Fee structure (3-year history)
    "infrastructure": Facilities, hostels, scholarships
}
```

## 3. Data Flow Architecture

### 3.1 College Information Retrieval Flow

```
User (University Frontend)
    ↓ [Search for college]
    ├─→ GET /api/college-statistics?college_name=X
    │
Go Backend (college_controller.go)
    ├─→ Check Redis Cache (fast path)
    ├─→ If miss → Query MongoDB → Cache to Redis
    │
Response Structure (CollegeStats model):
{
  basic_info: { college_name, rankings, student_statistics, faculty_staff, student_history}
  ug_programs: [programs]
  pg_programs: [programs]
  phd_programs: [programs]
  placements: { year, packages, rates, recruiters, 3-year history}
  fees: { UG/PG/PhD costs, scholarships }
  infrastructure: { hostel, library, transport, facilities }
  approval_status: "pending" | "approved"
  serper_sections: { raw data from Serper API }
}
```

### 3.2 Data Acquisition & Normalization Flow

```
Admin Request
    ↓ [Trigger new college scraping]
    ├─→ POST /api/college/validate (college name)
    │
Go Backend
    ├─→ Calls Groq API (via AI service)
    ├─→ Validates college exists
    │
Python API (serper_api.py)
    ├─→ Initiates WebSocket connection
    ├─→ For each query_category:
    │   ├─→ Builds curl command
    │   ├─→ Calls Serper API (Google Search AI)
    │   ├─→ Parses structured JSON response
    │   ├─→ Broadcasts status via WebSocket
    │   └─→ Sends to Go backend
    │
Go Backend (serper_service.go)
    ├─→ Normalizes response
    ├─→ Maps to CollegeStats schema
    ├─→ Stores in MongoDB with approval_status="pending"
    ├─→ Caches in Redis
    └─→ Broadcasts via RabbitMQ to connected clients
```

### 3.3 Assessment Flow

```
Authenticated User
    ↓ [Register for assessment]
    ├─→ POST /api/{test_type}/register
    ├─→ Stored in MongoDB (test registration collection)
    │
    ├─→ [Admin approves registration]
    ├─→ Assessment becomes available
    │
    ├─→ [Get questions]
    ├─→ GET /api/{test_type}/questions
    ├─→ Backend loads from MongoDB or Redis
    │
    ├─→ [Submit answers]
    ├─→ POST /api/{test_type}/submit
    │   ├─→ Score calculation
    │   ├─→ Result generation
    │   ├─→ Certificate URL generation
    │
    └─→ [View results]
        └─→ GET /api/{test_type}/result
            └─→ Return scored & interpreted results
            
Assessment Types:
├── Psychometric (scoring based on responses)
├── MBTI (personality dimensions)
├── Cognitive (IQ/knowledge testing)
├── PESCIO (career aptitude)
└── Behavioral (soft skills assessment)
```

### 3.4 Real-time Updates via WebSocket

```
Go Backend (websocket_routes.go)
    ├─→ Receives WebSocket upgrade request
    ├─→ Maintains connection pool
    │
Data Event
    ├─→ RabbitMQ publishes event
    ├─→ Cache invalidation consumer
    ├─→ Broadcasts to all connected clients
    │
Use Cases:
├─ Live college scraping progress
├─ Real-time test result updates
├─ Admin notifications
└─ Search analytics streaming
```

## 4. Key Files & Their Purpose

### Go Backend Structure

#### Routes & Routing
| File | Purpose | Endpoints |
|------|---------|-----------|
| `routes/routes.go` | Main router setup, CORS, flow control | `/api/health`, `/api/version` |
| `routes/auth_routes.go` | Authentication endpoints | `/api/auth/signup`, `/api/auth/login`, `/api/auth/verify-email` |
| `routes/college/college_routes.go` | College data endpoints | `/api/college-statistics`, `/api/search`, `/api/all-colleges` |
| `routes/admin/admin_routes.go` | Admin-only endpoints | College management, assessments, Redis cache |
| `routes/assessment_routes.go` | Assessment endpoints | `/api/{test_type}/register/questions/submit/result` |

#### Controllers
| File | Purpose |
|------|---------|
| `controllers/college/college_controller.go` | Fetch college stats, validate names, search |
| `controllers/college/analytics_controller.go` | Search analytics tracking |
| `controllers/auth/auth.go` | User signup, login, JWT generation |
| `controllers/assessment/*` | Test management for each assessment type |

#### Models (Database Schemas)
| File | Purpose |
|------|---------|
| `models/college.go` | CollegeStats with 100+ fields; nested structures for rankings, fees, placements |
| `models/user.go` | User profile, authentication tokens, verification |
| `models/psychometric.go` | PsychometricRegistration, Questions, Results |
| `models/mbti.go` | MBTI test structures with personality dimensions |
| `models/test.go` | Generic test framework, user answers, confidence tracking |

#### Services
| File | Purpose |
|------|---------|
| `services/ai/serper_service.go` | Serper API integration, JSON schema generation |
| `services/ai/groq_service.go` | Groq API for college name validation |
| `services/ai/gemini_service.go` | Gemini API for AI responses |
| `services/college/college_service.go` | Business logic for college data |
| `services/auth/auth.go` | JWT creation/validation, password hashing |
| `services/cache/cache.go` | Redis operations, caching logic |
| `services/messaging/rabbitmq.go` | RabbitMQ producer/consumer, event broadcasting |
| `services/realtime/realtime.go` | WebSocket management |

#### Configuration & Utilities
| File | Purpose |
|------|---------|
| `config/database.go` | MongoDB connection, collection initialization |
| `config/redis.go` | Redis/Dragonfly connection setup |
| `middleware/auth.go` | JWT validation, role-based access (admin) |
| `middleware/cors.go` | CORS policy configuration |
| `utils/response.go` | JSON response formatting helpers |

### Python Backend (college_scraper)

| File | Purpose |
|------|---------|
| `serper_api.py` | FastAPI server with Serper integration, WebSocket support |
| `serper.py` | Core Serper API functionality, curl commands, JSON parsing |
| `groq_college_validator.py` | Groq API integration for college validation |
| `normalizer.py` | Data normalization & schema mapping |
| `requirements.txt` | Dependencies (FastAPI, pymongo, redis, requests) |
| `docker-compose.yml` | MongoDB, Redis, college-scraper container setup |

### Frontend (University)

#### Configuration & Utils
| File | Purpose |
|------|---------|
| `lib/config.ts` | API endpoints, WebSocket URLs, environment vars |
| `contexts/AuthContext` | User auth state management |
| `hooks/useCountUp.ts` | Animation utilities for statistics |

#### Key Pages
| File | Purpose |
|------|---------|
| `app/college-details/[name]/page.tsx` | College information display, charts, detailed stats |
| `app/user-dashboard/test-results/TestResultsClient.tsx` | Test result visualization |
| `app/user-dashboard/psychometric-result/page.tsx` | Psychometric-specific result display + certificate |
| `app/api/universities/route.ts` | Next.js API route for college listing |
| `app/api/dontsettle/route.ts` | College filtering/advanced search API |

#### Components
| File | Purpose |
|------|---------|
| `components/home/dontsettle/com/UniversityList.tsx` | University card list with rankings, programs |
| N/A | Each assessment type has dedicated UI components |

## 5. Technology Stack

### Backend Technologies

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **HTTP Server** | Gorilla Mux (Go) | REST API routing |
| **Primary DB** | MongoDB 6.0 | NoSQL document storage |
| **Cache Layer** | Redis 7 (Dragonfly compatible) | Session & query caching (1hr TTL) |
| **Message Queue** | RabbitMQ | Event broadcasting, async tasks |
| **WebSocket** | Gorilla WebSocket | Real-time connections |
| **Authentication** | JWT (golang-jwt/v5) | Token-based auth, role management |
| **Hashing** | golang.org/x/crypto | Password hashing (bcrypt) |
| **Email** | Gomail (SMTP) | Email notifications |
| **Python Runtime** | FastAPI 0.104.1 | Data acquisition API |
| **External APIs** | Serper, Groq, Gemini | College search, validation, AI |

### Frontend Technologies

| Technology | Purpose |
|-----------|---------|
| **Framework** | Next.js 16.1.1 (React 19) | Server-side rendering, API routes |
| **Styling** | Tailwind CSS 3.4.15 | Utility-first styling |
| **Charts** | Chart.js 4.5.1, ZingChart | Data visualization |
| **HTTP Client** | Axios 1.13.2 | API requests |
| **Animations** | Intersection Observer, requestAnimationFrame | Smooth UI transitions |
| **Export** | jsPDF, html2canvas | PDF/image generation |
| **Icons** | Lucide React | SVG icon library |

### Development/DevOps

| Technology | Purpose |
|-----------|---------|
| **Containerization** | Docker | Application containerization |
| **Orchestration** | docker-compose | Multi-service orchestration |
| **Code Quality** | ESLint, TypeScript | Linting & type checking |
| **Build Tools** | PostCSS, Autoprefixer | CSS processing |
| **Package Managers** | npm, pnpm, go mod | Dependency management |

### Deployment

| Platform | Use Case |
|----------|----------|
| **Render.yaml** | Deployment configuration for Go backend |
| **Environment Config** | `.env` files for secrets, API keys |
| **Version Control** | Git (evidenced by standard structure) |

## 6. Database Schema Overview

### College Details Collection (Massive Document)
```typescript
{
  _id: ObjectId
  college_name: string
  short_name: string
  established: number
  institution_type: string
  country: string
  location: string
  website: string
  about: string
  summary: string
  
  // Programs
  ug_programs: [string]
  pg_programs: [string]
  phd_programs: [string]
  departments: [string]
  
  // Rankings Data
  rankings: {
    nirf_2025: any
    nirf_2024: any
    qs_world: any
    qs_asia: any
  }
  rankings_history: [{year, rank, source}]
  
  // Student Demographics
  student_statistics_detail: {
    total_enrollment: number
    ug_students: number
    pg_students: number
    phd_students: number
  }
  student_history: {
    student_count_comparison_last_3_years: [{year, total, ug, pg, phd}]
    student_gender_ratio: {total_male, total_female, percentages}
    international_students: {total_count, countries, percent}
  }
  
  // Faculty & Infrastructure
  faculty_staff_detail: {total_faculty, student_faculty_ratio, phd_percent}
  infrastructure: [{facility, details}]
  hostel_details: {available, capacity, type}
  
  // Placements & Careers
  placements: {year, highest_package, average_package, rate}
  placement_comparison_last_3_years: [{year, avg_pkg, rate}]
  gender_based_placement_last_3_years: [{year, male_cnt, female_cnt, %}]
  sector_wise_placement_last_3_years: [{year, sector, companies, %}]
  top_recruiters: [string]
  
  // Finances
  fees: {UG: {per_year, total_course}, PG: {...}, PhD: {...}}
  fees_by_year: [{year, UG: {...}, PG: {...}, PhD: {...}}]
  scholarships_detail: [{name, amount, currency, eligibility, provider}]
  
  // Meta
  approval_status: "pending" | "approved"
  created_at: ISO8601
  updated_at: ISO8601
  approved_by: string (admin ID)
  
  // Raw Data
  serper_sections: {raw response from Serper API}
  raw_data: {catch-all for unmapped fields}
}
```

### Users Collection
```typescript
{
  _id: ObjectId
  name: string
  email: string (unique)
  password: string (hashed, never sent)
  role: "user" | "admin"
  date_of_birth: ISO8601
  age: number
  student_type: "undergrad" | "postgrad" | "professional"
  is_verified: boolean
  verification_token: string (optional)
  reset_token_expiry: ISO8601
  created_at: ISO8601
  updated_at: ISO8601
  last_login: ISO8601
}
```

### Assessment Results Collections
```typescript
// mavti_test_results, cognitive_test_results, etc.
{
  _id: ObjectId
  user_id: string (ref to users)
  email: string
  name: string
  test_type: "mvti" | "cognitive" | "mbti" | "psychometric" | "pescio" | "behavioral"
  
  // Answers
  answers: [{question_id, question, selected_option, correct_option, is_correct, score}]
  
  // Scoring
  total_score: number
  max_score: number
  percentage: number
  
  // Results
  interpretation: string (for psychometric)
  mbti_type: string (for MBTI)
  certificate_url: string
  
  // Metadata
  total_time_spent: number (seconds)
  is_completed: boolean
  completed_at: ISO8601
  created_at: ISO8601
  updated_at: ISO8601
}
```

## 7. API Endpoints Summary

### Authentication
- `POST /api/auth/signup` - User registration
- `POST /api/auth/login` - User login
- `GET /api/auth/verify-email` - Email verification
- `POST /api/auth/resend-verification` - Resend verification email
- `GET /api/auth/me` - Get current user (protected)

### College Data
- `GET /api/college-statistics?college_name=X` - Get full college info
- `GET /api/all-colleges` - List all colleges (paginated)
- `GET /api/search?university_name=X` - Search colleges
- `GET /api/countries` - List all countries
- `GET /api/colleges-by-country?country=X` - Filter by country
- `POST /api/college/validate` - Validate college name
- `GET /api/most-searched` - Analytics endpoint

### Assessments (All protected with `/api/{test_type}/`)
- `POST /api/[test_type]/register` - Register for test
- `GET /api/[test_type]/registration` - Get registration status
- `GET /api/[test_type]/questions` - Fetch test questions
- `POST /api/[test_type]/submit` - Submit answers
- `GET /api/[test_type]/result` - Get scored result

### Admin Endpoints
- `POST /api/admin/college/*` - College management
- `POST /api/admin/assessment/*` - Assessment management
- `POST /api/admin/redis/*` - Cache control
- `GET /api/admin/user/*` - User management

### System
- `GET /api/health` - Health check
- `GET /api/version` - API version
- `GET /check/automate` - Automation status

### WebSocket
- `/ws` - WebSocket connection for real-time updates

## 8. Authentication & Authorization

### JWT Flow
```
User Login (POST /api/auth/login)
    ↓ [Verify credentials]
    ├─→ Hash password check
    ├─→ Generate JWT token
    ├─→ Token expires in configurable duration
    │
    └─→ Response: {token, user}

Subsequent Requests (Protected Routes)
    ↓ [Include Authorization header]
    ├─→ "Authorization: Bearer {token}"
    │
    ├─→ AuthMiddleware validates
    ├─→ Extract claims: user_id, email, role
    ├─→ Set headers for downstream handlers
    │
    └─→ Request proceeds or 401 Unauthorized
```

### Role-Based Access Control
```
Roles:
├─ "user" → Can access own assessments/results
├─ "admin" → Full system access (/api/admin/*)
│
AdminMiddleware
    ├─→ Checks X-User-Role header = "admin"
    └─→ Denies with 403 Forbidden if not admin
```

## 9. Caching Strategy

### Cache Layers
```
Request Flow with Caching:
GET /api/college-statistics?college_name=X
    ↓
    ├─→ Check Redis Cache (Key: "college:X")
    ├─→ If HIT → Return cached CollegeStats (1-hour TTL)
    ├─→ If MISS → Query MongoDB
    ├─→ Store in Redis with 1-hour expiry
    ├─→ Return to client
    
    When data updates:
    ├─→ RabbitMQ publishes cache invalidation event
    ├─→ Consumer deletes Redis key
    ├─→ Next request rebuilds cache
```

### What Gets Cached
- College statistics (full documents)
- Assessment questions (question banks)
- Search results
- User test sessions

## 10. Message Queue (RabbitMQ) Usage

### Event Types
```
cache_events exchange:
├─ college.updated → Invalidate college cache
├─ assessment.completed → Notify admin
├─ test.started → Track in analytics
│
Consumers:
├─ Cache Invalidation Consumer
└─ Analytics Consumer
```

## 11. Deployment Architecture

### Container Services (docker-compose.yml)
```yaml
services:
  mongodb:
    image: mongo:6.0
    - Port: 27017
    - Volume: mongodb_data
    
  redis:
    image: redis:7-alpine
    - Port: 6379
    
  college-scraper:
    build: ./college_scraper
    - Port: 8501
    - Dependencies: mongodb, redis
```

### Environment Variables (ok.env)
```
GEMINI_API_KEY=...
GROQ_API_KEY=...
MONGO_URI=mongodb://192.168.14.50:27017/tru
PORT=9000
ENVIRONMENT=development
REDIS_HOST=localhost
REDIS_PORT=6379
SMTP_HOST=smtp.gmail.com
ADMIN_EMAIL=...
JWT_SECRET=...
RABBITMQ_URL=amqp://...
```

## 12. Key Integration Points

### External APIs
```
1. Serper API (Search)
   └─→ Fetches college information from web
   └─→ Returns structured JSON per query
   
2. Groq API (Validation)
   └─→ Validates college names
   └─→ Improves data quality
   
3. Gemini API (AI Responses)
   └─→ Generates rich descriptions
   └─→ Creates recommendations
   
4. Email Service (SMTP)
   └─→ User verification
   └─→ Password reset
   └─→ Admin notifications
```

### Data Normalization Pipeline
```
Raw Serper Response
    ↓ (Python: serper.py)
    ├─→ Extract JSON from markdown
    ├─→ Parse and clean
    ├─→ Handle missing fields
    
    ↓ (Python: normalizer.py)
    ├─→ Map to CollegeStats schema
    ├─→ Validate data types
    ├─→ Enrich with inferred data
    
    ↓ (Go: serper_service.go)
    ├─→ Final validation
    ├─→ Store to MongoDB
    ├─→ Cache to Redis
    └─→ Broadcast via RabbitMQ
```

## 13. High-Level Data Processing Statistics

### College Data Complexity
- **Basic Info Query**: ~50 JSON fields
- **Programs Query**: Variable (10-100+ programs)
- **Placements Query**: 3-year historical data + gender/sector breakdown
- **Fees Query**: UG/PG/PhD costs across 3 years
- **Infrastructure Query**: Various facility types + scholarships

### Assessment Data
- **Questions per test**: 50-100+ questions
- **Data per response**: Question ID, selected option, correctness, time spent, bookmarks, hints
- **Results metrics**: Total score, percentage, interpretation, certificate URL

### User Base
- Multiple roles (user, admin)
- Support for different student types (undergrad, postgrad, professional)
- Email verification & password reset pipelines

---

## Summary Matrix

| Aspect | Technology | Details |
|--------|-----------|---------|
| **Core Backend** | Go + Gorilla Mux | Port 9000, handles all business logic |
| **Primary Database** | MongoDB | "tru-main" database, 10+ collections |
| **Cache** | Redis/Dragonfly | 1-hour TTL for college data & questions |
| **Real-time** | WebSocket + RabbitMQ | Live updates, event broadcasting |
| **Frontends** | Next.js 16 + React 19 | University (3000), Cougem (custom) |
| **Data Acquisition** | Python + FastAPI | Serper integration, normalization |
| **Auth** | JWT + Middleware | Role-based access control |
| **External APIs** | Serper, Groq, Gemini | Search, validation, AI |
| **DevOps** | Docker + docker-compose | Containerized services |

---

This architecture enables:
✅ Scalable real-time college information platform
✅ Multi-type assessment systems with detailed analytics
✅ Robust data acquisition with web scraping
✅ WebSocket-driven real-time features
✅ Microservices-ready with event-driven caching
✅ Comprehensive user authentication & role management
