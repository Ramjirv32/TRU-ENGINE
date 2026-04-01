# Component Interaction & Dependencies Matrix

## Frontend-Backend Communication Matrix

### University (Next.js 16) ↔ Go Backend (Port 9000)

| Frontend Feature | API Endpoint | HTTP Method | Payload | Response | Cache? |
|------------------|--------------|------------|---------|----------|--------|
| **Search Colleges** | `/api/search` | GET | `?university_name=X` | `[colleges]` | Redis |
| **Get All Colleges** | `/api/all-colleges` | GET | (paginated) | `{colleges, total, pages}` | Redis |
| **College Details** | `/api/college-statistics` | GET | `?college_name=X` | `{full CollegeStats}` | Redis 1hr |
| **List Countries** | `/api/countries` | GET | - | `[countries]` | Redis |
| **Filter by Country** | `/api/colleges-by-country` | GET | `?country=X` | `[colleges]` | Redis |
| **Top Searched** | `/api/most-searched` | GET | - | `[colleges]` | Redis |
| **Sign Up** | `/api/auth/signup` | POST | `{name, email, password, dob}` | `{token, user}` | No |
| **Login** | `/api/auth/login` | POST | `{email, password}` | `{token, user}` | No |
| **Get Current User** | `/api/auth/me` | GET | Bearer token | `{user}` | No |
| **Verify Email** | `/api/auth/verify-email` | GET | `?token=X` | `{status}` | No |
| **Register Assessment** | `/api/{type}/register` | POST | `{type, reason}` | `{registration_id}` | No |
| **Get Questions** | `/api/{type}/questions` | GET | - | `[questions]` | Redis |
| **Submit Test** | `/api/{type}/submit` | POST | `{answers[]}` | `{results}` | No |
| **Get Results** | `/api/{type}/result` | GET | - | `{result}` | No |
| **Validate College** | `/api/college/validate` | POST | `{college_name}` | `{is_valid}` | No |

### Assessment Types (All Protected by AuthMiddleware)
- `/api/psychometric/*` - Psychology assessment
- `/api/mbti/*` - Personality test
- `/api/cognitive/*` - IQ/Knowledge test
- `/api/pescio/*` - Career aptitude
- `/api/behavioral/*` - Soft skills

## Backend Service Dependencies Graph

```
┌─────────────────────────────────────────────────────────────┐
│                     HTTP Request                            │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    Router (Gorilla Mux)                     │
├─────────────────────────────────────────────────────────────┤
│ Applies: CorsMiddleware → AuthMiddleware → AdminMiddleware  │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              Route-Specific Handlers                        │
├────────────────┬───────────────────┬──────────────┬─────────┤
│   Auth Routes  │ College Routes    │ Assessment   │ Admin   │
│                │                   │ Routes       │ Routes  │
└────────┬───────┴──────────┬────────┴──────┬───────┴─────┬───┘
         ↓                  ↓               ↓             ↓
┌─────────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────┐
│ Auth Service    │ │ College Svc  │ │ Assessment   │ │ Admin Svc│
├─────────────────┤ ├──────────────┤ ├──────────────┤ ├──────────┤
│ - CreateAdmin   │ │ - Retrieve   │ │ - Register   │ │- Manage  │
│ - JWT Generate  │ │ - Search     │ │ - Score      │ │  Colleges│
│ - JWT Validate  │ │ - Validate   │ │ - Store      │ │- Manage  │
│ - Hash Password │ │ - Analytics  │ │ - Generate   │ │  Users   │
└────────┬────────┘ └──────┬───────┘ │  Results     │ │- Cache   │
         │               │           └──────┬───────┘ │  Control │
         │               │                  │         └──────┬───┘
         │               │    ┌─────────────┘                │
         ↓               ↓    ↓                              ↓
┌─────────────────────────────────────────────────────────────┐
│                    Cache Service (Redis)                    │
├─────────────────────────────────────────────────────────────┤
│ Keys: college:{name}, questions:{type}, session:{id}        │
│ TTL: 1 hour (configurable)                                 │
└────────────────────────┬────────────────────────────────────┘
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                MongoDB (tru-main database)                     │
├─────────────────────────────────────────────────────────────┤
│ Collections: college_details, users, test_results, etc.    │
└─────────────────────────────────────────────────────────────┘

         ↑
         │ (Broadcast events)
         │
┌─────────────────────────────────────────────────────────────┐
│              Messaging Service (RabbitMQ)                  │
├─────────────────────────────────────────────────────────────┤
│ Exchange: college_events                                   │
│ Queue: cache_invalidation, analytics                       │
└────────┬────────────────────────────────────────┬──────────┘
         │                                        │
         ↓                                        ↓
    Cache Consumer              Analytics/Realtime Consumer
```

## Data Flow: College Statistics Request

```mermaid
Request: GET /api/college-statistics?college_name=IIT_Madras

1. Router receives request
   ├─→ Applies CorsMiddleware
   └─→ Routes to college.GetCollegeStatistics()

2. Controller: college_controller.go::GetCollegeStatistics()
   ├─→ Extract college_name from query
   ├─→ Call collegeService.GetCollegeStatistics()
   └─→ Return JSON response

3. Service: college_service.go::GetCollegeStatistics()
   ├─→ Check Redis Cache
   │   ├─→ HIT: Return cached CollegeStats
   │   └─→ MISS: Continue to step 4
   └─→ Query MongoDB college_details collection
       ├─→ Filter: {college_name: "IIT Madras"}
       ├─→ Get complete document
       └─→ Store in Redis (1hr TTL)

4. Return to Controller
   ├─→ Format JSON response
   └─→ Send to client
```

## Data Flow: Assessment Submission

```mermaid
Request: POST /api/psychometric/submit

1. AuthMiddleware
   ├─→ Check "Authorization: Bearer {token}"
   ├─→ Validate JWT signature
   ├─→ Set X-User-ID, X-User-Email, X-User-Role headers
   └─→ Continue to handler

2. Controller: assessment/psychometric/controller.go
   ├─→ Extract user_id from header
   ├─→ Parse request body: {answers: [...]}
   └─→ Call psychometricService.SubmitTest()

3. Service: assessment/psychometric/service.go
   ├─→ Load user's registration
   ├─→ Validate test hasn't been completed
   ├─→ Calculate scores:
   │   ├─→ For each answer:
   │   │   ├─→ Compare with correct_option
   │   │   ├─→ Score points
   │   │   └─→ Generate interpretation
   │   └─→ Total score
   ├─→ Generate certificate URL
   └─→ Create PsychometricResult document

4. Database Storage
   ├─→ Insert to mvti_test_results collection
   ├─→ Mark registration as completed
   └─→ Clear Redis session cache

5. Event Broadcasting
   ├─→ Publish test.completed event to RabbitMQ
   └─→ Analytics consumer logs metrics

6. Response to Client
   └─→ Return {total_score, percentage, interpretation, certificate_url}
```

## External API Integration Points

### Serper API (College Search)
```
Go Backend (main.go starts up)
    ↓
Services initialize
    ├─→ serper_service.go::InitializeSerperService()
    │
    When college data needed:
    ├─→ admin triggers: POST /api/admin/college/scrape
    ├─→ Validation: collegeService.ValidateCollegeName()
    │   └─→ groq_service.go::ValidateViaGroq()
    │
    ├─→ Calls Python API: POST http://localhost:8501/scrape
    │
    Python API (serper_api.py)
    ├─→ For each query category:
    │   ├─→ Build curl command with Serper API key
    │   ├─→ GET https://serpapi.com/search
    │   ├─→ Parse JSON response
    │   └─→ Broadcast via WebSocket
    │
    ├─→ normalize → store to MongoDB
    ├─→ cache to Redis
    ├─→ publish RabbitMQ event
    │
    Go Backend receives completion
    └─→ Return success to admin UI
```

### Groq API (Validation)
```
Input: college_name (e.g., "IIT Madras")
    ↓
Go Backend
    ├─→ groq_service.go::ValidateCollegeName()
    ├─→ POST https://api.groq.com/validate
    ├─→ Verify college exists
    └─→ Return boolean
```

### Gemini API (AI Responses)
```
Input: college context
    ↓
Go Backend
    ├─→ gemini_service.go::GenerateDescription()
    ├─→ POST to Gemini API
    ├─→ Generate rich content
    └─→ Return formatted text
```

### SMTP (Email)
```
Trigger: User verification needed
    ↓
Go Backend
    ├─→ authService.SendVerificationEmail()
    ├─→ gomail.Dialer.Dial("smtp.gmail.com:587")
    ├─→ Compose email with verification token
    ├─→ Send to user email
    └─→ Return status

Trigger: Password reset
    ↓
Similar flow with reset token
```

## Middleware Execution Order

```
Incoming HTTP Request
    ↓
1. Gorilla Router receives
    ↓
2. CORS Middleware
   ├─→ Checks allowed origins
   ├─→ Adds CORS headers
   └─→ If OPTIONS request, respond immediately
    ↓
3. Auth-Required Routes
   ├─→ AuthMiddleware
   │   ├─→ Extract Bearer token from Authorization header
   │   ├─→ Validate JWT signature
   │   ├─→ Extract claims: user_id, email, role
   │   ├─→ Set request headers: X-User-ID, X-User-Email, X-User-Role
   │   └─→ Call next handler
   │
   ├─→ (Optional) AdminMiddleware
   │   ├─→ Check X-User-Role == "admin"
   │   └─→ Allow or reject with 403 Forbidden
   │
    └─→ Protected Handler receives decorated request
        ├─→ Extract user_id from r.Header.Get("X-User-ID")
        ├─→ Access controlled resource
        └─→ Return response
    ↓
4. Response sent to client with CORS headers
```

## Cache Invalidation Flow

```
Event: College data updated
    ↓
Admin calls PUT /api/admin/college/{id}
    ↓
Go Backend
    ├─→ Update MongoDB document
    ├─→ Publish RabbitMQ event:
    │   {
    │     "type": "college.updated",
    │     "college_id": "...",
    │     "timestamp": "..."
    │   }
    └─→ Return 200 OK
    ↓
RabbitMQ
    ├─→ Route event to cache_invalidation queue
    └─→ Consumers subscribed
        ↓
Cache Consumer (caching_service.go)
    ├─→ Receive event
    ├─→ Delete Redis key: college:{college_name}
    ├─→ Log: "Cache invalidated for college X"
    └─→ Acknowledge message
    ↓
Next Request
    ├─→ GET /api/college-statistics?college_name=X
    ├─→ Redis MISS (key deleted)
    ├─→ Query MongoDB (fresh data)
    ├─→ Re-cache to Redis
    └─→ Return to client
```

## WebSocket Real-time Flow

```
1. Client connects
   ├─→ GET /ws (WebSocket upgrade)
   ├─→ Go Backend
   │   ├─→ Accept WebSocket connection
   │   ├─→ Add connection to pool (ConnectionManager)
   │   └─→ Listen for messages
   └─→ Connection established

2. Event occurs (e.g., college scraping)
   ├─→ Python API completes query
   ├─→ Broadcasts via RabbitMQ:
   │   {
   │     "event": "college.scraping_progress",
   │     "college": "IIT Madras",
   │     "section": "placements",
   │     "status": "completed"
   │   }
   └─→ Message to exchange

3. Message Queue
   ├─→ RabbitMQ routes to consumers
   └─→ Realtime consumer in Go Backend
       ├─→ Receives message
       ├─→ Converts to JSON
       └─→ Broadcasts to all connected WebSocket clients

4. Client receives
   ├─→ WebSocket message received
   ├─→ Parse JSON
   ├─→ Update UI in real-time
   └─→ Display progress

5. Disconnect
   ├─→ Client closes connection or network error
   ├─→ Go Backend
   │   ├─→ Remove connection from pool
   │   └─→ Clean up resources
   └─→ Connection closed
```

## Authentication & Authorization Flow

```
┌─────────────────────────────── SIGNUP ───────────────────────────────┐
User submits form
    ↓
POST /api/auth/signup
    {name, email, password, date_of_birth}
    ↓
auth/signup controller
    ├─→ Validate input (email format, password length)
    ├─→ Check if email exists (MongoDB query)
    ├─→ Hash password: crypto.bcrypt.hash()
    ├─→ Generate verification_token (random)
    ├─→ Insert to users collection:
    │   {
    │     email: "user@example.com",
    │     password: "$2a$10$...(hashed)",
    │     verification_token: "...",
    │     is_verified: false,
    │     role: "user",
    │     created_at: now
    │   }
    ├─→ Send verification email via SMTP
    └─→ Return 201 Created

User clicks email link
    ↓
GET /api/auth/verify-email?token=X
    ↓
Controller
    ├─→ Find user by verification_token
    ├─→ Update is_verified: true
    ├─→ Clear verification_token
    └─→ Redirect to login

└─────────────────────────────────────────────────────────────────────┘

┌──────────────────────────────── LOGIN ───────────────────────────────┐
User submits credentials
    ↓
POST /api/auth/login
    {email, password}
    ↓
auth/login controller
    ├─→ Find user by email
    ├─→ Compare password: crypto.bcrypt.compare()
    ├─→ If not verified: reject
    ├─→ Generate JWT token:
    │   {
    │     user_id: "...",
    │     email: "user@example.com",
    │     role: "user",
    │     exp: now + 24 hours
    │   }
    │   Signed with JWT_SECRET
    ├─→ Update last_login: now
    └─→ Return {token, user}

Client stores token in localStorage/cookie
    ↓
Subsequent requests
    └─→ Include: Authorization: Bearer {token}

└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────── AUTHORIZATION ────────────────────────────┐
Protected route: GET /api/psychometric/result

Middleware: AuthMiddleware
    ├─→ Extract Authorization header
    ├─→ Parse "Bearer {token}"
    ├─→ Call jwt.ValidateToken(token)
    │   ├─→ Verify signature with JWT_SECRET
    │   ├─→ Check expiration
    │   ├─→ Extract claims
    │   └─→ Return claims or error
    ├─→ Set request headers with user info
    └─→ Continue to handler

Protected route: POST /api/admin/college/scrape

After AuthMiddleware, AdminMiddleware
    ├─→ Check X-User-Role == "admin"
    ├─→ If not: return 403 Forbidden
    └─→ If yes: continue to handler

Handler executes
    ├─→ Has user_id, email, role in context
    ├─→ Perform operation
    └─→ Return response

└─────────────────────────────────────────────────────────────────────┘
```

## Collection Relationships

```
users
  ├─ _id (ObjectId)
  ├─ email (unique index)
  └─ role

college_details
  ├─ _id (ObjectId)
  ├─ college_name (indexed)
  ├─ country (indexed)
  └─ approval_status (indexed)

assessment_registrations (per type)
  ├─ _id (ObjectId)
  ├─ user_id → users._id
  ├─ status: "pending" | "approved" | "rejected"
  └─ approvedBy → users._id

test_results (per assessment type)
  ├─ _id (ObjectId)
  ├─ user_id → users._id
  ├─ email → users.email
  └─ answers: [{question_id, ...}]

search_analytics
  ├─ _id (ObjectId)
  ├─ user_id → users._id (optional, anonymous searches too)
  ├─ query (text indexed)
  └─ timestamp (indexed, used for aggregation)
```

## Performance Optimization Points

| Optimization | Location | Benefit |
|--------------|----------|---------|
| Redis Cache (1hr) | college_statistics, questions | Reduce DB queries by 90% |
| Database Indexing | college_name, country, user_id | Fast queries for filters |
| Pagination | /api/all-colleges | Handle large datasets |
| JWT TokenMiddleware | Every protected route | Prevent repeated DB lookups |
| Connection Pooling | MongoDB, Redis | Reuse connections |
| Async RabbitMQ | cache invalidation | Non-blocking background tasks |
| WebSocket Broadcast | Real-time updates | Single connection per client |
| Lazy Loading | Frontend components | Faster initial page load |
| Chart.js Charts | College details page | Pre-calculate on server |

## Testing Critical Paths

### Path 1: User Registration → Assessment → Results
```
1. POST /api/auth/signup
2. GET /api/auth/verify-email?token=X
3. POST /api/auth/login
4. POST /api/psychometric/register
5. GET /api/psychometric/questions
6. POST /api/psychometric/submit
7. GET /api/psychometric/result
```

### Path 2: Admin College Scraping
```
1. POST /api/admin/college/validate {college_name}
2. POST /api/admin/college/scrape {college_name}
   (Triggers Python API)
3. Monitor WebSocket for progress
4. GET /api/college-statistics?college_name=X
5. POST /api/admin/college/{id}/approve
```

### Path 3: Search & Filter
```
1. GET /api/all-colleges (get initial list)
2. GET /api/countries (populate filter)
3. GET /api/colleges-by-country?country=X
4. GET /api/search?university_name=X
5. GET /api/college-statistics?college_name=X (drill down)
```
