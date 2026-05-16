"""
Mineral AI Tracker - Health Check Endpoint (PRD v9.0 Phase 9.9)
Version: 10.5
Description: System health monitoring endpoint for observability
PRD v10.0 Phase 10.5: Added proxy health check and statistics endpoints
"""

from typing import Dict, Any
from fastapi import APIRouter
from loguru import logger
import httpx
import psycopg2
from psycopg2.extras import RealDictCursor
from utils.proxy_pool import get_proxy_pool

router = APIRouter(prefix="/api/health", tags=["health"])


def get_db_connection():
    """Get database connection"""
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="mineral_ai_tracker",
        user="mineral_user",
        password="mineralpass123",
        cursor_factory=RealDictCursor
    )


@router.get("/")
async def health_check() -> Dict[str, Any]:
    """
    Comprehensive health check endpoint (PRD v9.0 Phase 9.9)
    
    Checks status of:
    a) Database connection
    b) Ollama process
    c) API keys in system_settings
    """
    health_status = {
        "status": "healthy",
        "checks": {
            "database": {"status": "unknown", "message": ""},
            "ollama": {"status": "unknown", "message": ""},
            "api_keys": {"status": "unknown", "message": ""}
        }
    }
    
    # Check database connection
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                health_status["checks"]["database"] = {
                    "status": "ok",
                    "message": "Database connection successful"
                }
        finally:
            conn.close()
    except Exception as e:
        health_status["checks"]["database"] = {
            "status": "error",
            "message": f"Database connection failed: {e}"
        }
        health_status["status"] = "degraded"
    
    # Check Ollama process
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            response = await client.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                health_status["checks"]["ollama"] = {
                    "status": "ok",
                    "message": "Ollama process running"
                }
            else:
                health_status["checks"]["ollama"] = {
                    "status": "error",
                    "message": f"Ollama returned status {response.status_code}"
                }
                health_status["status"] = "degraded"
    except Exception as e:
        health_status["checks"]["ollama"] = {
            "status": "error",
            "message": f"Ollama not accessible: {e}"
        }
        health_status["status"] = "degraded"
    
    # Check API keys in system_settings
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT fmp_api_key IS NOT NULL as has_fmp_key,
                           telegram_bot_token IS NOT NULL as has_telegram_key
                    FROM system_settings LIMIT 1
                """)
                row = cur.fetchone()
                if row:
                    has_fmp = row.get("has_fmp_key", False)
                    has_telegram = row.get("has_telegram_key", False)
                    
                    if has_fmp:
                        health_status["checks"]["api_keys"] = {
                            "status": "ok",
                            "message": "API keys loaded (FMP configured)"
                        }
                    else:
                        health_status["checks"]["api_keys"] = {
                            "status": "warning",
                            "message": "FMP API key not configured"
                        }
                        health_status["status"] = "degraded"
                else:
                    health_status["checks"]["api_keys"] = {
                        "status": "warning",
                        "message": "System settings not initialized"
                    }
                    health_status["status"] = "degraded"
        finally:
            conn.close()
    except Exception as e:
        health_status["checks"]["api_keys"] = {
            "status": "error",
            "message": f"Failed to check API keys: {e}"
        }
        health_status["status"] = "degraded"
    
    return health_status


@router.get("/proxy-stats")
async def proxy_stats() -> Dict[str, Any]:
    """
    Get proxy pool statistics (PRD v10.0 Phase 10.5)
    
    Returns:
    - Total proxies
    - Healthy proxies
    - Per-proxy statistics (success rate, consecutive failures, health status)
    """
    proxy_pool = get_proxy_pool()
    return proxy_pool.get_stats()


@router.post("/proxy-health-check")
async def proxy_health_check() -> Dict[str, Any]:
    """
    Trigger proxy health check (PRD v10.0 Phase 10.5)
    
    Tests all proxies in the pool and updates their health status.
    """
    proxy_pool = get_proxy_pool()
    await proxy_pool.health_check()
    return {
        "status": "completed",
        "stats": proxy_pool.get_stats()
    }


__all__ = ["router"]
