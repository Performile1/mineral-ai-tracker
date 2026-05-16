# Mineral AI Tracker - Master Analysis Document (Phase 10-12)

**Project Version:** 12.1 (The Enterprise Edition - Authentication, Async Processing & Event Correlation)
**Phase 10.1:** NextAuth & RLS (Authentication & Data Isolation)
**Phase 10.3:** The Async Broker (Celery & Redis)
**Phase 12.1:** The Event Correlation Engine (Financial News Correlation)
**Analysis Date:** 2026-05-15
**Purpose:** Critical analysis of authentication, async processing, and event correlation implementation

---

## Executive Summary

The Mineral AI Tracker platform has been significantly enhanced with three major infrastructure improvements:

**Phase 10.1 (Authentication & Data Isolation):** Implemented NextAuth with Google OAuth and Row Level Security (RLS) to enable multi-user support while ensuring strict data isolation between users. This transformation from a single-user system to a multi-user platform is critical for scaling and monetization.

**Phase 10.3 (Async Broker):** Implemented Celery + Redis for asynchronous task processing, enabling long-running AI operations to run in the background without blocking API responses. This improves system responsiveness and enables proper task queue management for high-volume processing.

**Phase 12.1 (Event Correlation Engine):** Built a sophisticated system that correlates financial news events with price movements, rendering events as interactive markers on price charts. The system uses a Source Authority Matrix to weight news sources by credibility and Phi-3 AI to generate one-sentence summaries.

**Key Architecture Changes:**
- Authentication: NextAuth v4 with Google OAuth provider
- Database: Added users table, user_id columns, and RLS policies
- Async Processing: Celery v5.3 + Redis v5.0 with connection pooling
- Event Storage: asset_events table with authority scoring and AI summaries
- Frontend: PriceChart component with interactive event markers and custom tooltips

---

## Phase 10.1: Authentication & Data Isolation Analysis

### Database Schema Changes

**File:** `db/init/07_add_users_table.sql`
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255),
    image TEXT,
    email_verified TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);
```

**Critical Analysis:**
- ✅ Proper UUID primary key for NextAuth compatibility
- ✅ Email uniqueness constraint prevents duplicate accounts
- ✅ Timestamps for audit trail
- ✅ Image field for profile pictures
- ⚠️ Missing email verification workflow (NextAuth supports this but not implemented)
- ⚠️ No password field (OAuth-only, which is acceptable but limits flexibility)

**File:** `db/init/06_add_user_id_to_signals.sql`
```sql
ALTER TABLE investment_signals ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE SET NULL;
ALTER TABLE user_portfolio ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;
ALTER TABLE paper_trades ADD COLUMN user_id UUID REFERENCES users(id) ON DELETE CASCADE;
```

**Critical Analysis:**
- ✅ ON DELETE CASCADE for user_portfolio and paper_trades ensures data cleanup
- ✅ ON DELETE SET NULL for investment_signals preserves analytics data
- ✅ Indexes on user_id for query performance
- ⚠️ Existing rows have NULL user_id (migration strategy needed for production data)
- ⚠️ No default user_id for single-user legacy mode (could cause issues during transition)

**File:** `db/init/08_add_rls_policies.sql`
```sql
ALTER TABLE investment_signals ENABLE ROW LEVEL SECURITY;
CREATE POLICY user_isolation_signals ON investment_signals
  FOR ALL TO authenticated_user
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());
```

**Critical Analysis:**
- ✅ Proper RLS enablement on user-specific tables
- ✅ Policies use auth.uid() for Supabase compatibility
- ✅ USING clause for SELECT, WITH CHECK for INSERT/UPDATE
- ❌ **CRITICAL ISSUE:** RLS policies reference `auth.uid()` which is Supabase-specific, but the platform uses local PostgreSQL
- ❌ **CRITICAL ISSUE:** No `authenticated_user` role defined in local PostgreSQL
- ❌ **CRITICAL ISSUE:** RLS will not work in local PostgreSQL environment without Supabase authentication system
- ⚠️ Need to implement application-level filtering instead of database-level RLS for local PostgreSQL

### Frontend Authentication Implementation

**File:** `frontend/lib/auth-config.ts`
```typescript
export const authOptions = {
  adapter: PostgresAdapter(pool),
  providers: [GoogleProvider({ clientId, clientSecret })],
  session: { strategy: "database" },
  callbacks: { async session({ session, user }) {
    if (session.user) session.user.id = user.id
    return session
  }}
}
```

**Critical Analysis:**
- ✅ Proper NextAuth v4 configuration
- ✅ PostgresAdapter for database session storage
- ✅ Session callback injects user.id into session
- ⚠️ Uses @auth/postgres-adapter which was removed from package.json due to install errors
- ⚠️ Direct PostgreSQL connection in frontend (violates best practices - should use API)
- ⚠️ Hardcoded database credentials in frontend code (security risk in production)

**File:** `frontend/lib/auth.ts`
```typescript
export async function requireAuth() {
  const session = await getServerSession(authOptions)
  if (!session || !session.user) redirect("/auth/signin")
  return session.user
}
```

**Critical Analysis:**
- ✅ Clean authentication helper functions
- ✅ Server-side session validation
- ✅ Proper redirect on unauthenticated access
- ⚠️ No role-based access control (all authenticated users have same permissions)
- ⚠️ No session timeout configuration

**File:** `frontend/app/layout.tsx`
```typescript
const user = await getCurrentUser()
{user ? (
  <div className="flex items-center gap-3">
    <span>{user.name || user.email}</span>
    <a href="/api/auth/signout">Sign Out</a>
  </div>
) : (
  <Link href="/api/auth/signin" className="bg-primary text-white px-4 py-2">Sign In</Link>
)}
```

**Critical Analysis:**
- ✅ Clean login/logout UI
- ✅ Conditional rendering based on auth state
- ✅ User-friendly sign-in button
- ⚠️ No user profile/settings link
- ⚠️ No credits display (credits system added in Phase 12 but not shown in UI)

### Backend Authentication Integration

**File:** `backend/api/intelligence.py`
```python
async def analyze_discovery(request: AnalyzeRequest, user_id: Optional[str] = None):
    if user_id:
        cur.execute("SELECT credits_remaining FROM users WHERE id = %s", (user_id,))
        credits = row["credits_remaining"]
        if credits < 1:
            raise HTTPException(status_code=402, detail="Insufficient credits")
```

**Critical Analysis:**
- ✅ Credit check before analysis (monetization gating)
- ✅ Returns proper HTTP 402 Payment Required error
- ✅ Deducts credit after successful analysis
- ⚠️ user_id is optional parameter (no authentication enforcement)
- ⚠️ No authentication middleware to validate user_id from session
- ⚠️ Credits system exists but no Stripe integration for payments

---

## Phase 10.3: Async Broker Analysis

### Infrastructure Changes

**File:** `docker-compose.yml`
```yaml
redis:
  image: redis:alpine
  ports: ["6379:6379"]
  volumes: [redis_data:/data]

celery_worker:
  build: ./backend
  command: celery -A backend.worker.celery_app worker --loglevel=info
  environment:
    - REDIS_URL=redis://redis:6379/0
  depends_on: [redis, postgres, ollama]
```

**Critical Analysis:**
- ✅ Proper Redis service configuration with data persistence
- ✅ Celery worker with correct command and dependencies
- ✅ Environment variables properly configured
- ✅ Health check dependencies (redis, postgres, ollama)
- ⚠️ No Redis password configured (security risk in production)
- ⚠️ No Redis persistence configuration (AOF/RDB)
- ⚠️ No Celery worker autoscaling (single worker instance)
- ⚠️ No Celery beat for scheduled tasks

**File:** `backend/requirements.txt`
```
celery>=5.3.0
redis>=5.0.0
```

**Critical Analysis:**
- ✅ Latest stable versions of Celery and Redis
- ✅ Compatible with existing dependencies
- ⚠️ No celery[redis] extras bundle (might miss Redis-specific features)
- ⚠️ No kombu for advanced message broker options

### Celery Implementation

**File:** `backend/worker/celery_app.py`
```python
celery_app = Celery(
    'mineral_ai',
    broker=os.getenv('REDIS_URL', 'redis://redis:6379/0'),
    backend=os.getenv('REDIS_URL', 'redis://redis:6379/0')
)
```

**Critical Analysis:**
- ✅ Proper Celery app configuration
- ✅ Environment variable for flexibility
- ✅ Same URL for broker and backend (acceptable for development)
- ⚠️ No task serialization configuration (default pickle is security risk)
- ⚠️ No task time limits (could cause runaway tasks)
- ⚠️ No task retry configuration
- ⚠️ No worker concurrency limits

**File:** `backend/utils/database.py`
```python
connection_pool = pool.ThreadedConnectionPool(
    minconn=2, maxconn=10,
    host=os.getenv("POSTGRES_HOST"),
    database=os.getenv("POSTGRES_DB"),
    user=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD")
)
```

**Critical Analysis:**
- ✅ Proper connection pooling for Celery workers
- ✅ Reasonable min/max connection limits
- ✅ Environment variable configuration
- ⚠️ No connection timeout configuration
- ⚠️ No connection health checking
- ⚠️ Pool size might be insufficient for high concurrency

### API Integration

**File:** `backend/api/intelligence.py`
```python
USE_CELERY = os.getenv("USE_CELERY", "False").lower() == "true"

if USE_CELERY:
    from worker.celery_app import celery_app
    from worker.tasks import task_run_analysis
    task = task_run_analysis.delay(ticker=ticker, user_id=user_id, is_public=False)
    return {"status": "processing", "task_id": task.id}
```

**Critical Analysis:**
- ✅ USE_CELERY flag for sync/async fallback
- ✅ Conditional Celery imports (works in both modes)
- ✅ Returns task_id for polling
- ✅ Graceful fallback to synchronous processing
- ⚠️ No task priority configuration
- ⚠️ No task result expiration (Redis memory growth)
- ⚠️ No task cancellation endpoint

**File:** `backend/api/intelligence.py` (Status Endpoint)
```python
@router.get("/status/{task_id}")
async def get_task_status(task_id: str):
    result = celery_app.AsyncResult(task_id)
    return {"task_id": task_id, "status": result.status, "result": result.result if result.ready() else None}
```

**Critical Analysis:**
- ✅ Clean status endpoint implementation
- ✅ Returns status and result when ready
- ⚠️ No task timeout (client could poll indefinitely)
- ⚠️ No rate limiting on status endpoint
- ⚠️ No task deletion after completion (memory leak)

### Frontend Polling

**File:** `frontend/components/WatchlistStalker.tsx`
```typescript
useEffect(() => {
  if (taskId && stage === "processing") {
    intervalRef.current = setInterval(async () => {
      const res = await fetch(`${apiUrl}/api/watchlist/status/${taskId}`)
      const data = await res.json()
      if (data.status === "SUCCESS") {
        setStage("done")
        setResult(data.result)
      } else if (data.status === "FAILURE") {
        setError(`Analysis failed: ${data.error}`)
      }
    }, 5000)
  }
}, [taskId, stage])
```

**Critical Analysis:**
- ✅ Proper polling interval (5 seconds)
- ✅ Cleanup on component unmount
- ✅ Handles SUCCESS and FAILURE states
- ✅ 5-minute timeout (60 attempts)
- ⚠️ No exponential backoff (could overwhelm server)
- ⚠️ No polling cancellation on user action
- ⚠️ No visual feedback during polling

---

## Phase 12.1: Event Correlation Engine Analysis

### Database Schema

**File:** `db/init/11_add_asset_events.sql`
```sql
CREATE TABLE asset_events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ticker VARCHAR(20) NOT NULL,
    published_at TIMESTAMP WITH TIME ZONE NOT NULL,
    title TEXT NOT NULL,
    url TEXT,
    source_authority_score DECIMAL(3,2) NOT NULL CHECK (source_authority_score >= 0.1 AND source_authority_score <= 1.0),
    ai_summary TEXT,
    price_impact_4h DECIMAL(10,4),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    CONSTRAINT unique_event UNIQUE (ticker, published_at, url)
);
```

**Critical Analysis:**
- ✅ Proper UUID primary key
- ✅ Authority score constraint (0.1-1.0)
- ✅ Unique constraint prevents duplicate events
- ✅ Indexes on ticker and published_at for performance
- ✅ Composite index on ticker + published_at for common queries
- ⚠️ No user_id column (events are global, not per-user)
- ⚠️ No event type/category column (authority score only)
- ⚠️ price_impact_4h is nullable (events without price data)
- ⚠️ No event status (pending/processed/failed)

### Authority Matrix Implementation

**File:** `backend/utils/authority_matrix.py`
```python
def get_authority_score(source_type: str, source_name: Optional[str] = None) -> float:
    if any(keyword in source_type_lower for keyword in ['financial_report', 'annual_report', 'sec_filing']):
        return 1.0
    elif any(keyword in source_type_lower for keyword in ['press_release', 'pr']):
        return 0.8
    else:
        return 0.4
```

**Critical Analysis:**
- ✅ Clear three-tier authority system
- ✅ Keyword-based classification
- ✅ Source name as additional context
- ✅ Returns default 0.4 for unknown sources
- ⚠️ Hardcoded keywords (no configuration)
- ⚠️ No learning/adaptation capability
- ⚠️ No source reputation tracking
- ⚠️ No manual override capability

### Event Processing Pipeline

**File:** `backend/worker/tasks/event_tasks.py`
```python
@shared_task
def process_event_summary(event_id: str) -> dict:
    ollama = OllamaClient()
    summary = ollama.generate_completion(
        prompt=f"Summarize this financial news in exactly one short sentence: {row['title']}",
        model=os.getenv("OLLAMA_PHI3_MODEL", "phi3")
    )
    cur.execute("UPDATE asset_events SET ai_summary = %s WHERE id = %s", (summary, event_id))
```

**Critical Analysis:**
- ✅ Proper Celery task for async processing
- ✅ Uses Phi-3 for fast summarization
- ✅ Clear prompt constraint ("exactly one short sentence")
- ⚠️ No error handling for Ollama failures
- ⚠️ No summarization retry logic
- ⚠️ No quality validation of summary
- ⚠️ No fallback to original title if summary fails

**File:** `backend/worker/tasks/event_tasks.py` (Price Impact)
```python
@shared_task
def calculate_price_impact(event_id: str) -> dict:
    four_hours_later = published_at + timedelta(hours=4)
    # Placeholder: Calculate price impact from historical data
    price_impact = None  # Will be populated when price data is available
```

**Critical Analysis:**
- ✅ Proper task structure
- ✅ 4-hour window for price impact
- ⚠️ **CRITICAL ISSUE:** Price impact calculation is not implemented (placeholder)
- ⚠️ No OHLC data table reference
- ⚠️ No price data fetching logic
- ⚠️ No handling of missing price data
- ⚠️ No market hours consideration (4 hours could span overnight)

### Events API

**File:** `backend/api/events.py`
```python
@router.get("/{ticker}")
async def get_events(ticker: str, start_date: Optional[str] = None, 
                   end_date: Optional[str] = None, min_authority: Optional[float] = None):
    query = "SELECT * FROM asset_events WHERE ticker = %s"
    if start_date: query += " AND published_at >= %s"
    if min_authority: query += " AND source_authority_score >= %s"
    query += " ORDER BY published_at DESC LIMIT %s"
```

**Critical Analysis:**
- ✅ Flexible filtering (date range, authority score)
- ✅ Proper pagination with LIMIT
- ✅ Returns total count
- ✅ Upper bound on LIMIT (500) for performance
- ⚠️ No caching (frequent queries could be slow)
- ⚠️ No event pagination offset (only first 500)
- ⚠️ No event type filtering
- ⚠️ No price impact filtering

**File:** `backend/api/events.py` (Create Event)
```python
@router.post("/{ticker}", status_code=201)
async def create_event(ticker: str, title: str, url: Optional[str], 
                      source_type: str, published_at: str):
    authority_score = get_authority_score(source_type, source_name)
    cur.execute("INSERT INTO asset_events (...) VALUES (...) ON CONFLICT DO NOTHING")
```

**Critical Analysis:**
- ✅ Automatic authority score calculation
- ✅ ON CONFLICT DO NOTHING prevents duplicates
- ✅ Returns created event ID
- ⚠️ No authentication required (anyone can create events)
- ⚠️ No rate limiting (could be abused)
- ⚠️ No input validation on source_type
- ⚠️ No event deduplication beyond URL

### Frontend Visualization

**File:** `frontend/components/PriceChart.tsx`
```typescript
const authority = point.event.source_authority_score;
const size = authority >= 1.0 ? 8 : authority >= 0.8 ? 6 : 4;
const opacity = authority >= 1.0 ? 1.0 : authority >= 0.8 ? 0.8 : 0.5;
const color = point.event.price_impact_4h > 0 ? "#4F8A8B" : "#B35A44";
```

**Critical Analysis:**
- ✅ Dynamic marker sizing based on authority
- ✅ Dynamic opacity based on authority
- ✅ Color coding for price impact (green/red)
- ✅ ReferenceDot for precise positioning
- ⚠️ Hardcoded color values (should use Tailwind classes)
- ⚠️ No marker shape variation (all circles)
- ⚠️ No marker animation on hover
- ⚠️ No marker click action

**File:** `frontend/components/PriceChart.tsx` (CustomTooltip)
```typescript
function CustomTooltip({ hoveredEvent }) {
  return (
    <div>
      <h4>{hoveredEvent.title}</h4>
      <p>{hoveredEvent.ai_summary}</p>
      <span style={{ color: impactColor }}>
        Price Impact: {hoveredEvent.price_impact_4h.toFixed(2)}%
      </span>
    </div>
  )
}
```

**Critical Analysis:**
- ✅ Clean tooltip layout
- ✅ Shows AI summary
- ✅ Color-coded price impact
- ✅ Link to source
- ⚠️ No tooltip positioning logic (might go off-screen)
- ⚠️ No tooltip z-index (might be covered by other elements)
- ⚠️ No tooltip delay on hover (might be distracting)
- ⚠️ No tooltip animation

---

## Overall Assessment

### Strengths

**Phase 10.1 (Authentication):**
- ✅ Clean NextAuth v4 implementation
- ✅ Proper database schema for multi-user support
- ✅ User-friendly login/logout UI
- ✅ Credits system for monetization
- ✅ Session-based authentication
- ✅ OAuth integration (Google)

**Phase 10.3 (Async Broker):**
- ✅ Proper Celery + Redis architecture
- ✅ Connection pooling for database efficiency
- ✅ Sync/async fallback with USE_CELERY flag
- ✅ Task status endpoint for polling
- ✅ Frontend polling with timeout
- ✅ Docker service configuration

**Phase 12.1 (Event Correlation):**
- ✅ Innovative Source Authority Matrix
- ✅ AI-powered event summarization
- ✅ Interactive chart markers
- ✅ Dynamic visual styling
- ✅ Custom tooltips with rich information
- ✅ Flexible API filtering

### Weaknesses

**Phase 10.1 (Authentication):**
- ❌ **CRITICAL:** RLS policies use Supabase-specific auth.uid() (won't work with local PostgreSQL)
- ❌ **CRITICAL:** No authenticated_user role in local PostgreSQL
- ❌ **CRITICAL:** Direct PostgreSQL connection in frontend (security risk)
- ❌ **CRITICAL:** Hardcoded database credentials in frontend
- ❌ No application-level user filtering (RLS won't work)
- ❌ No authentication middleware in backend
- ❌ No role-based access control
- ❌ No email verification workflow
- ❌ No password reset capability
- ❌ No user profile management
- ❌ Credits system exists but no payment integration

**Phase 10.3 (Async Broker):**
- ❌ No Redis password (security risk)
- ❌ No Redis persistence configuration
- ❌ No Celery worker autoscaling
- ❌ No task serialization configuration (pickle security risk)
- ❌ No task time limits (runaway tasks)
- ❌ No task retry configuration
- ❌ No worker concurrency limits
- ❌ No task result expiration (memory leak)
- ❌ No task cancellation endpoint
- ❌ No exponential backoff in polling
- ❌ No Celery beat for scheduled tasks

**Phase 12.1 (Event Correlation):**
- ❌ **CRITICAL:** Price impact calculation not implemented (placeholder)
- ❌ No OHLC data table for price calculations
- ❌ No authentication on events API (anyone can create events)
- ❌ No rate limiting on events API
- ❌ No event caching (performance issue)
- ❌ No event pagination offset
- ❌ No market hours consideration in price impact
- ❌ Hardcoded authority keywords
- ❌ No source reputation tracking
- ❌ No manual override capability
- ❌ Events are global (no per-user isolation)

### Critical Issues Requiring Immediate Attention

1. **RLS Incompatibility:** RLS policies use Supabase-specific functions but platform uses local PostgreSQL. Solution: Implement application-level filtering in backend API endpoints.

2. **Frontend Database Connection:** Direct PostgreSQL connection in frontend violates security best practices. Solution: Move database operations to backend API.

3. **Hardcoded Credentials:** Database credentials exposed in frontend code. Solution: Use environment variables and backend proxy.

4. **Price Impact Calculation:** Event correlation engine has placeholder implementation. Solution: Implement OHLC data table and price calculation logic.

5. **No Authentication Enforcement:** Backend APIs accept optional user_id without validation. Solution: Add authentication middleware to validate user_id from session.

6. **No Event Authentication:** Events API has no authentication. Solution: Add authentication middleware to events API.

### Recommendations

**Immediate (High Priority):**
1. Implement application-level user filtering in all backend endpoints
2. Remove direct database connection from frontend
3. Move all database operations to backend API
4. Implement authentication middleware for backend
5. Complete price impact calculation implementation
6. Add authentication to events API

**Short-term (Medium Priority):**
1. Implement Redis password and persistence
2. Add task time limits and retry logic
3. Add event caching with Redis
4. Implement event pagination
5. Add rate limiting to public APIs
6. Add role-based access control

**Long-term (Low Priority):**
1. Implement email verification workflow
2. Add password reset capability
3. Add user profile management
4. Implement Stripe payment integration
5. Add Celery worker autoscaling
6. Add source reputation tracking

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Next.js)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │  NextAuth   │  │ PriceChart  │  │WatchlistStk │       │
│  │  (Google)   │  │ (Events)    │  │ (Polling)   │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                  │                  │               │
│         └──────────────────┴──────────────────┘               │
│                            │                                  │
└────────────────────────────┼──────────────────────────────────┘
                             │ HTTP/REST
┌────────────────────────────┼──────────────────────────────────┐
│                  Backend (FastAPI)                            │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ Events API  │  │ Intelligence │  │   Auth MW    │       │
│  │ (CRUD)      │  │  (Celery)    │  │ (Middleware) │       │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘       │
│         │                  │                  │               │
│         └──────────────────┴──────────────────┘               │
│                            │                                  │
┌────────────────────────────┼──────────────────────────────────┐
│              Infrastructure Layer                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │ PostgreSQL   │  │    Redis     │  │   Celery     │       │
│  │ (Users/Data) │  │  (Queue)     │  │  (Workers)   │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│  ┌──────────────┐  ┌──────────────┐                           │
│  │    Ollama    │  │   FMP API    │                           │
│  │  (Phi-3)     │  │  (External)   │                           │
│  └──────────────┘  └──────────────┘                           │
└─────────────────────────────────────────────────────────────┘
```

---

## Testing Strategy

### Unit Tests Needed
- [ ] Authority matrix scoring logic
- [ ] Event creation validation
- [ ] Price impact calculation
- [ ] Authentication middleware
- [ ] User filtering in API endpoints

### Integration Tests Needed
- [ ] NextAuth login flow
- [ ] Celery task execution
- [ ] Event processing pipeline
- [ ] Frontend-backend authentication
- [ ] Price chart event rendering

### E2E Tests Needed
- [ ] User login → Create event → View on chart
- [ ] Credit deduction flow
- [ ] Async task polling
- [ ] Multi-user data isolation

---

## Deployment Checklist

**Pre-deployment:**
- [ ] Remove hardcoded credentials from frontend
- [ ] Implement application-level user filtering
- [ ] Add authentication middleware to backend
- [ ] Complete price impact calculation
- [ ] Add Redis password
- [ ] Configure Redis persistence
- [ ] Add task time limits
- [ ] Add rate limiting to public APIs

**Post-deployment:**
- [ ] Monitor Celery worker performance
- [ ] Monitor Redis memory usage
- [ ] Monitor database connection pool
- [ ] Monitor authentication failures
- [ ] Monitor event processing queue
- [ ] Set up Grafana dashboards for new metrics

---

## Conclusion

The implementation of Phase 10.1, 10.3, and 12.1 represents significant architectural improvements to the Mineral AI Tracker platform:

**Authentication (10.1):** Successfully implemented NextAuth with Google OAuth and multi-user database schema. However, RLS policies are incompatible with local PostgreSQL and require application-level filtering implementation.

**Async Processing (10.3):** Successfully implemented Celery + Redis for background task processing with proper connection pooling and sync/async fallback. Missing production-hardening features like Redis security and task limits.

**Event Correlation (12.1):** Successfully implemented innovative Source Authority Matrix and interactive chart visualization. Price impact calculation is incomplete (placeholder) and requires OHLC data implementation.

**Overall Assessment:** The foundation is solid but requires production hardening before deployment. Critical issues (RLS incompatibility, frontend database connection, missing authentication enforcement) must be resolved. The architecture is well-designed and follows best practices where implemented.

**Risk Level:** MEDIUM-HIGH (due to critical security and implementation gaps)
**Production Readiness:** 60% (backend 70%, frontend 50%)
**Estimated Time to Production:** 2-3 weeks (with focused effort on critical issues)

---

## Critical Hotfix Sprint - Completion Note (2026-05-15)

The Critical Hotfix Sprint identified in this analysis has now been completed. All scoped API endpoints now require JWT authentication via `Depends(get_current_user)` from `backend/api/deps.py`, and queries against user-bound tables filter on `user_id` (Application-Level Filtering).

### Protected routers (now require JWT)
- `alerts.py` (5 endpoints) - `alert_configs` queries filter on `user_id`; `INSERT/UPDATE` write authenticated `user_id`.
- `intelligence.py` (5 endpoints) - `investment_signals` queries filter on `user_id`; `/analyze` credit-check uses authenticated `user_id` (legacy `user_id` query param removed).
- `backtesting.py` (6 endpoints).
- `admin.py` (5 endpoints) - JWT required; role-based admin check remains a TODO.
- `settings.py` (5 endpoints, incl. vault) - JWT required.
- `stripe.py` (3 user endpoints) - JWT required; cross-user access on `/subscription-status/{user_id}` and `/cancel-subscription/{user_id}` now returns 403.
- `discoveries.py` (3 endpoints).
- `manufacturing.py` (3 endpoints).
- `execution.py` (2 endpoints).
- `assets.py` (5 endpoints).
- `watchlist.py` (3 endpoints).
- `events.py` POST (auth required), GET uses `get_optional_user` (events are global).
- `portfolio/correlation.py` (4 endpoints) - all callers of `get_portfolio_positions()` now pass `user_id`; hardcoded DB credentials removed, replaced by shared `utils.database.get_db_connection`.

### Explicit exceptions (intentionally public)
- `health.py` - liveness/readiness must be unauthenticated.
- `market.py` - public market data proxy.
- `hive.py` - anonymous Global Pulse aggregate (`is_public = TRUE`).
- `macro.py` - public macro indicators.
- `stripe.py` `POST /webhook` - verified via Stripe signature, not JWT.
- `alerts.py` `AlertManager.load_configs()` - internal cache loading all configs for the dispatcher (not exposed via endpoint).

### Remaining technical debt
- ~~`backend/api/deps.py` `get_current_user` is still a **placeholder**~~ **RESOLVED (2026-05-16)** in the Phase 11/12 Consolidation sprint. `get_current_user` now validates HS256 signatures via `python-jose` against `NEXTAUTH_SECRET` and returns the user from the JWT payload.
- ~~Frontend must be updated to send the NextAuth JWT in the `Authorization: Bearer <token>` header~~ **RESOLVED (2026-05-16)**: new `frontend/lib/apiClient.ts` `apiFetch` wrapper attaches the Bearer token from `session.accessToken`. `auth-config.ts` mints the backend-compatible JWT in the `jwt` callback via `jose.SignJWT`. All 12 protected frontend call sites migrated. Public endpoints (`/api/macro/*`, `/api/market/*`, `/api/hive/*`) intentionally still use raw `fetch`.
- `admin.py` endpoints need a role check (`current_user["role"] == "admin"`) once user roles are introduced.
- Several Stripe endpoint docstrings now appear after the cross-user check (cosmetic only; functionally fine).
- Internal cron/Celery callers of newly-protected endpoints (if any) must either call services directly or be issued service tokens.

### Phase 11/12 Consolidation Sprint - Completion Note (2026-05-16)

Idempotent run of the four-step PRD prompt. Most of steps 1-4 were already in place from prior sprints; this sprint closed the three remaining functional gaps and tightened `events.py GET`:

**Backend**
- `backend/api/deps.py` - replaced placeholder with real HS256 JWT validation using `python-jose`. Reads `NEXTAUTH_SECRET` from env (warns-and-falls-back in dev). Extracts `sub`/`email`/`name` from payload. Maps `ExpiredSignatureError` and `JWTError` to 401.
- `backend/requirements.txt` - added `python-jose[cryptography]>=3.3.0`.
- `backend/worker/tasks/event_tasks.py` - added `process_event_pipeline = process_new_event` alias to match Phase 12.1 spec 3.1 (no behavioural change; existing `.delay()` callers unaffected).
- `backend/api/events.py` - `GET /api/events/{ticker}` switched from `get_optional_user` to `get_current_user` per spec 4.1. Now requires authentication.

**Frontend**
- New `frontend/lib/apiClient.ts` exports `apiFetch(path, options)` that reads the NextAuth session via `getSession()` and attaches `Authorization: Bearer <session.accessToken>` automatically. Also exports `apiGetJson` convenience helper.
- `frontend/lib/auth-config.ts` - `jwt` callback now mints a backend-compatible HS256 JWT via `jose.SignJWT` (signed with `NEXTAUTH_SECRET`, 24h TTL, includes `sub`/`email`/`name`) and stashes it on `token.accessToken`. `session` callback exposes it as `session.accessToken`.
- `frontend/package.json` - added `jose ^5.2.0`.
- Migrated 12 protected call sites to `apiFetch`: `app/dashboard/page.tsx`, `app/backtesting/page.tsx`, `app/settings/page.tsx`, `app/settings/alerts/page.tsx`, `app/portfolio/risk/page.tsx`, `app/assets/[ticker]/page.tsx` (asset profile + watchlist), `app/screener/page.tsx`, `app/admin/dashboard/page.tsx`, `components/Portfolio.tsx`, `components/WatchlistStalker.tsx`, `components/ShadowPortfolio.tsx`, `components/PriceChart.tsx`.
- Intentionally untouched (public endpoints): `components/GlobalPulse.tsx` (`/api/macro/pulse`), `components/LiveTicker.tsx` (`/api/market/quote`), hive consensus call in `app/assets/[ticker]/page.tsx` (`/api/hive/consensus`).
- Stub components with commented-out fetch (`ScenarioSimulator.tsx`, `DiscoveryRadar.tsx`, `MineralHeatmap.tsx`, `app/assets/page.tsx`) left as-is.

**Verification**
- `curl -H "Authorization: Bearer <invalid>" http://localhost:8000/api/events/AAPL` → 401 (was 200 with mock user before).
- With valid session JWT minted by NextAuth, the same request returns 200 and events render in `PriceChart`.

**Environment setup required**
- `NEXTAUTH_SECRET` must be set identically on the Next.js server **and** on the FastAPI backend process. Generate with `openssl rand -base64 32`.
- Set `ENVIRONMENT=production` on the backend in prod deployments - `backend/api/deps.py` now raises `RuntimeError` at import time if `NEXTAUTH_SECRET` is missing under that flag (no more silent insecure fallback).
- Optional `JWT_ALGORITHM` (default `HS256`) and `JWT_AUDIENCE` env vars supported on backend.

### Post-sprint cleanup (2026-05-16 PM)

**Production hardening (deps.py)**
- `backend/api/deps.py` - missing `NEXTAUTH_SECRET` now raises `RuntimeError` when `ENVIRONMENT=production`; dev still allows fallback with a loud warning.

**TypeScript cleanup (zero logic changes, only types)**
- `components/PortfolioCard.tsx` - replaced the imported `Asset` from `@/lib/schemas` with a local `PortfolioCardAsset` interface containing only the fields the card actually reads. Resolves the `asset_type/country_code/exchange/created_at/updated_at` missing-properties error from `Portfolio.tsx:163`.
- `components/WatchlistStalker.tsx` - added optional `articles?: StalkerArticle[]` to `StalkerResult`; declared local `elapsed` (computed from `startRef.current`) inside the status-line IIFE; typed the `.map((a, i) => ...)` callback explicitly.
- `components/IntelligenceCard.tsx` - props are now `signal?: IntelligenceSignal; asset_id?: string;`; component renders a placeholder when only an `asset_id` is supplied. Hooks (`useState` x4, `useCallback`) moved above the early return to satisfy React's Rules of Hooks.
