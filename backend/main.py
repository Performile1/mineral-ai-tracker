"""
Mineral AI Tracker - Main FastAPI Application
Version: 11.0
Description: Main application entry point with API routers + APScheduler
PRD v9.0: Added alerts, backtesting, and portfolio correlation routers
PRD v10.0 Phase 10.6: Added admin observability dashboard
PRD v10.0 Phase 11: Added Prometheus instrumentation for observability
PRD v10.0 Phase 11: Added security headers middleware
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from loguru import logger
import sys

# Phase 9.9: System Resilience - Rate Limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

# PRD v10.0 Phase 11: Prometheus instrumentation
from prometheus_fastapi_instrumentator import Instrumentator


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """PRD v10.0 Phase 11: Security headers middleware for all public endpoints"""
    
    async def dispatch(self, request, call_next):
        response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response

# Import API routers
from api.assets import router as assets_router
from api.discoveries import router as discoveries_router
from api.manufacturing import router as manufacturing_router
from api.stripe import router as stripe_router
from api.settings import router as settings_router
from api.intelligence import router as intelligence_router
from api.watchlist import router as watchlist_router
from api.market import router as market_router
from api.macro import router as macro_router
from api.execution import router as execution_router
from api.alerts import router as alerts_router
from api.backtesting import router as backtesting_router
from api.health import router as health_router
from api.hive import router as hive_router
from api.admin import router as admin_router
from api.events import router as events_router
from api.pulse import router as pulse_router

# Automation layer (PRD v8.3)
from scrapers.scheduler import start_scheduler, stop_scheduler

# Configure logger
logger.remove()
logger.add(sys.stdout, format="{time} | {level} | {message}", level="INFO")

# Phase 9.9: System Resilience - Rate Limiting Setup
limiter = Limiter(key_func=get_remote_address)
app = FastAPI(
    title="Mineral AI Tracker API",
    description="API for mineral asset tracking and analysis",
    version="11.0"
)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# PRD v10.0 Phase 11: Initialize Prometheus instrumentator
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_group_untemplated=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics"],
    env_var_name="METRICS_ENABLED",
    inprogress_labels=True,
)
instrumentator.instrument(app)

# CORS middleware - Restricted to localhost:3000 for security (Phase 9.9)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Restrict to frontend only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# PRD v10.0 Phase 11: Add security headers middleware
app.add_middleware(SecurityHeadersMiddleware)

# Register routers
app.include_router(assets_router)
app.include_router(discoveries_router)
app.include_router(manufacturing_router)
app.include_router(stripe_router)
app.include_router(settings_router)
app.include_router(intelligence_router)
app.include_router(watchlist_router)
app.include_router(market_router)
app.include_router(macro_router)
app.include_router(execution_router)
app.include_router(alerts_router)
app.include_router(backtesting_router)
app.include_router(health_router)
app.include_router(hive_router)
app.include_router(admin_router)
app.include_router(events_router)
app.include_router(pulse_router)


# Automation lifecycle (PRD v8.3)
@app.on_event("startup")
async def _start_automation() -> None:
    try:
        start_scheduler()
        # PRD v10.0 Phase 11: Expose Prometheus metrics on startup
        instrumentator.expose(app, include_in_schema=False, should_gzip=True)
        logger.info("Prometheus metrics exposed at /metrics")
    except Exception as e:
        logger.error(f"Failed to start scheduler: {e}")


@app.on_event("shutdown")
async def _stop_automation() -> None:
    stop_scheduler()

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "version": "8.3"}

# Root endpoint
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Mineral AI Tracker API",
        "version": "8.3",
        "endpoints": {
            "assets": "/api/assets",
            "discoveries": "/api/discoveries",
            "manufacturing": "/api/manufacturing",
            "settings": "/api/settings",
            "intelligence": "/api/intelligence",
            "health": "/health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
