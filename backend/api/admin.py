"""
Mineral AI Tracker - Admin Observability Dashboard (PRD v10.0 Phase 10.6)
Version: 10.6
Description: Admin dashboard for real-time system observability and analysis tracking
"""

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, Depends, Request

from api.deps import get_admin_user
from loguru import logger
from datetime import datetime, timedelta
from psycopg2.extras import RealDictCursor
from slowapi import Limiter
from slowapi.util import get_remote_address
from utils.database import get_db_connection, release_db_connection

limiter = Limiter(key_func=get_remote_address)

router = APIRouter(prefix="/api/admin", tags=["admin"])



@router.get("/dashboard")
async def get_admin_dashboard(
    current_user: dict = Depends(get_admin_user)
) -> Dict[str, Any]:
    """
    Get admin dashboard data (PRD v10.0 Phase 10.6)
    
    Returns:
    - Analysis success/failure rates
    - Total analyses today/week/month
    - System health metrics
    - Recent activity
    """
    dashboard_data = {
        "analysis_stats": {
            "total_today": 0,
            "total_week": 0,
            "total_month": 0,
            "success_rate_today": 0.0,
            "success_rate_week": 0.0,
            "success_rate_month": 0.0
        },
        "system_health": {
            "status": "unknown",
            "database": "unknown",
            "ollama": "unknown",
            "celery": "unknown",
            "redis": "unknown"
        },
        "recent_activity": [],
        "backtesting_stats": {
            "total_backtests": 0,
            "avg_return": 0.0,
            "best_strategy": None,
            "last_backtest_date": None
        }
    }
    
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Get analysis stats for today
                today = datetime.now().date()
                week_ago = (datetime.now() - timedelta(days=7)).date()
                month_ago = (datetime.now() - timedelta(days=30)).date()
                
                # Today's stats
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN signal_type IN ('BUY', 'STRONG_BUY') THEN 1 ELSE 0 END) as successful
                    FROM signals 
                    WHERE created_at >= %s
                """, (today,))
                today_stats = cur.fetchone()
                
                if today_stats:
                    dashboard_data["analysis_stats"]["total_today"] = today_stats["total"]
                    if today_stats["total"] > 0:
                        dashboard_data["analysis_stats"]["success_rate_today"] = (
                            (today_stats["successful"] / today_stats["total"]) * 100
                        )
                
                # Week's stats
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN signal_type IN ('BUY', 'STRONG_BUY') THEN 1 ELSE 0 END) as successful
                    FROM signals 
                    WHERE created_at >= %s
                """, (week_ago,))
                week_stats = cur.fetchone()
                
                if week_stats:
                    dashboard_data["analysis_stats"]["total_week"] = week_stats["total"]
                    if week_stats["total"] > 0:
                        dashboard_data["analysis_stats"]["success_rate_week"] = (
                            (week_stats["successful"] / week_stats["total"]) * 100
                        )
                
                # Month's stats
                cur.execute("""
                    SELECT 
                        COUNT(*) as total,
                        SUM(CASE WHEN signal_type IN ('BUY', 'STRONG_BUY') THEN 1 ELSE 0 END) as successful
                    FROM signals 
                    WHERE created_at >= %s
                """, (month_ago,))
                month_stats = cur.fetchone()
                
                if month_stats:
                    dashboard_data["analysis_stats"]["total_month"] = month_stats["total"]
                    if month_stats["total"] > 0:
                        dashboard_data["analysis_stats"]["success_rate_month"] = (
                            (month_stats["successful"] / month_stats["total"]) * 100
                        )
                
                # Get recent activity (last 10 signals)
                cur.execute("""
                    SELECT 
                        ticker,
                        signal_type,
                        confidence_score,
                        created_at,
                        is_public
                    FROM signals 
                    ORDER BY created_at DESC 
                    LIMIT 10
                """)
                recent_signals = cur.fetchall()
                
                dashboard_data["recent_activity"] = [
                    {
                        "ticker": sig["ticker"],
                        "signal_type": sig["signal_type"],
                        "confidence_score": float(sig["confidence_score"]) if sig["confidence_score"] else 0.0,
                        "created_at": sig["created_at"].isoformat() if sig["created_at"] else None,
                        "is_public": sig["is_public"]
                    }
                    for sig in recent_signals
                ]
                
                # Get system health status
                dashboard_data["system_health"]["database"] = "ok"
                
        finally:
            release_db_connection(conn)
    except Exception as e:
        logger.error(f"Failed to fetch dashboard data: {e}")
        dashboard_data["system_health"]["database"] = "error"
    
    return dashboard_data


@router.get("/analysis-timeline")
async def get_analysis_timeline(
    days: int = Query(7, description="Number of days to look back"),
    limit: int = Query(100, description="Maximum number of records"),
    current_user: dict = Depends(get_admin_user),
) -> Dict[str, Any]:
    """
    Get analysis timeline for admin dashboard (PRD v10.0 Phase 10.6)
    
    Args:
        days: Number of days to look back
        limit: Maximum number of records
    
    Returns:
        Timeline of analyses with success/failure tracking
    """
    timeline_data = []
    
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                start_date = (datetime.now() - timedelta(days=days)).date()
                
                cur.execute("""
                    SELECT 
                        ticker,
                        signal_type,
                        confidence_score,
                        created_at,
                        is_public,
                        user_id
                    FROM signals 
                    WHERE created_at >= %s
                    ORDER BY created_at DESC
                    LIMIT %s
                """, (start_date, limit))
                
                signals = cur.fetchall()
                
                timeline_data = [
                    {
                        "ticker": sig["ticker"],
                        "signal_type": sig["signal_type"],
                        "confidence_score": float(sig["confidence_score"]) if sig["confidence_score"] else 0.0,
                        "created_at": sig["created_at"].isoformat() if sig["created_at"] else None,
                        "is_public": sig["is_public"],
                        "user_id": str(sig["user_id"]) if sig["user_id"] else None,
                        "status": "success" if sig["signal_type"] in ["BUY", "STRONG_BUY", "HOLD"] else "neutral"
                    }
                    for sig in signals
                ]
                
        finally:
            release_db_connection(conn)
    except Exception as e:
        logger.error(f"Failed to fetch analysis timeline: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch timeline: {e}")
    
    return {
        "days": days,
        "total_analyses": len(timeline_data),
        "timeline": timeline_data
    }


@router.get("/performance-metrics")
async def get_performance_metrics(
    days: int = Query(30, description="Number of days to analyze"),
    current_user: dict = Depends(get_admin_user)
) -> Dict[str, Any]:
    """
    Get performance metrics for admin dashboard (PRD v10.0 Phase 10.6)
    
    Args:
        days: Number of days to analyze
    
    Returns:
        Performance metrics including Sharpe ratio, win rate, etc.
    """
    metrics = {
        "total_signals": 0,
        "buy_signals": 0,
        "sell_signals": 0,
        "hold_signals": 0,
        "avg_confidence": 0.0,
        "top_tickers": [],
        "signal_distribution": {}
    }
    
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                start_date = (datetime.now() - timedelta(days=days)).date()
                
                # Get signal distribution
                cur.execute("""
                    SELECT 
                        signal_type,
                        COUNT(*) as count,
                        AVG(confidence_score) as avg_conf
                    FROM signals 
                    WHERE created_at >= %s
                    GROUP BY signal_type
                """, (start_date,))
                
                distribution = cur.fetchall()
                
                total = sum(d["count"] for d in distribution)
                metrics["total_signals"] = total
                
                for d in distribution:
                    signal_type = d["signal_type"]
                    metrics["signal_distribution"][signal_type] = d["count"]
                    
                    if signal_type in ["BUY", "STRONG_BUY"]:
                        metrics["buy_signals"] += d["count"]
                    elif signal_type in ["SELL", "STRONG_SELL"]:
                        metrics["sell_signals"] += d["count"]
                    else:
                        metrics["hold_signals"] += d["count"]
                
                # Get top tickers
                cur.execute("""
                    SELECT 
                        ticker,
                        COUNT(*) as count
                    FROM signals 
                    WHERE created_at >= %s
                    GROUP BY ticker
                    ORDER BY count DESC
                    LIMIT 10
                """, (start_date,))
                
                top_tickers = cur.fetchall()
                metrics["top_tickers"] = [
                    {"ticker": t["ticker"], "count": t["count"]}
                    for t in top_tickers
                ]
                
        finally:
            release_db_connection(conn)
    except Exception as e:
        logger.error(f"Failed to fetch performance metrics: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {e}")
    
    return metrics


@router.get("/celery-status")
async def get_celery_status(
    current_user: dict = Depends(get_admin_user)
) -> Dict[str, Any]:
    """
    Get Celery queue status (PRD v10.0 Phase 11)
    
    Returns:
        Celery worker and queue status information
    """
    try:
        from worker.celery_app import celery_app
        
        # Get Celery worker stats
        inspect = celery_app.control.inspect()
        
        # Get active tasks
        active = inspect.active()
        active_count = sum(len(tasks) for tasks in (active.values() if active else {}))
        
        # Get scheduled tasks
        scheduled = inspect.scheduled()
        scheduled_count = sum(len(tasks) for tasks in (scheduled.values() if scheduled else {}))
        
        # Get reserved tasks
        reserved = inspect.reserved()
        reserved_count = sum(len(tasks) for tasks in (reserved.values() if reserved else {}))
        
        # Get registered tasks
        registered = inspect.registered()
        
        # Get worker stats
        stats = inspect.stats()
        
        return {
            "status": "ok",
            "active_tasks": active_count,
            "scheduled_tasks": scheduled_count,
            "reserved_tasks": reserved_count,
            "workers": len(active.keys()) if active else 0,
            "registered_tasks": list(registered.values())[0] if registered else [],
            "stats": stats
        }
    except Exception as e:
        logger.error(f"Failed to fetch Celery status: {e}")
        return {
            "status": "error",
            "error": str(e),
            "active_tasks": 0,
            "scheduled_tasks": 0,
            "reserved_tasks": 0,
            "workers": 0
        }


@router.get("/prometheus-metrics")
async def get_prometheus_metrics(
    current_user: dict = Depends(get_admin_user)
) -> Dict[str, Any]:
    """
    Get Prometheus metrics in JSON format (PRD v10.0 Phase 11)
    
    Returns:
        Prometheus metrics parsed into JSON for admin dashboard
    """
    try:
        import httpx
        
        # Fetch metrics from Prometheus endpoint
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get("http://localhost:9090/metrics")
            response.raise_for_status()
            metrics_text = response.text
        
        # Parse Prometheus metrics format
        metrics = {}
        for line in metrics_text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # Parse metric line
            if '{' in line:
                # Metric with labels
                parts = line.split('{')
                name = parts[0].strip()
                rest = parts[1].split('}')
                labels = rest[0].strip()
                value = float(rest[1].strip())
                
                if name not in metrics:
                    metrics[name] = []
                metrics[name].append({
                    "labels": labels,
                    "value": value
                })
            else:
                # Simple metric without labels
                parts = line.split()
                if len(parts) >= 2:
                    name = parts[0]
                    value = float(parts[1])
                    metrics[name] = value
        
        # Extract key metrics for dashboard
        key_metrics = {
            "http_requests_total": metrics.get("http_requests_total", 0),
            "http_request_duration_seconds": metrics.get("http_request_duration_seconds", 0),
            "celery_tasks_total": metrics.get("celery_tasks_total", 0),
            "celery_worker_tasks": metrics.get("celery_worker_tasks", 0),
            "db_connections_active": metrics.get("db_connections_active", 0),
        }
        
        return {
            "status": "ok",
            "metrics": metrics,
            "key_metrics": key_metrics
        }
    except Exception as e:
        logger.error(f"Failed to fetch Prometheus metrics: {e}")
        return {
            "status": "error",
            "error": str(e),
            "metrics": {},
            "key_metrics": {}
        }


# ---------------------------------------------------------------------------
# Force Refresh — Sprint 10.5 (The Panic Button)
# ---------------------------------------------------------------------------

async def _run_analysis_for_ticker(ticker: str, company_type: str) -> None:
    """Background task: re-analyse a single ticker after data purge."""
    try:
        from engines.nexus_engine import NexusEngine
        engine = NexusEngine()
        import asyncio
        loop = asyncio.get_event_loop()
        if company_type == "CONSUMER":
            await engine.analyze_manufacturer(ticker)
        else:
            await engine.analyze_miner(ticker)
        logger.info(f"Force Refresh: analysis complete for {ticker}")
    except Exception as exc:
        logger.error(f"Force Refresh background task failed for {ticker}: {exc}")


@router.post("/nodes/{ticker}/force-refresh", response_model=Dict[str, Any])
@limiter.limit("5/minute")
async def force_refresh_node(
    request: Request,
    ticker: str,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_admin_user),
) -> Dict[str, Any]:
    """
    Panic Button — purge stale extracted_data for a node and re-queue a
    fresh Nexus Engine analysis.  Returns immediately; analysis runs async.
    """
    ticker = ticker.upper()
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT asset_ticker, company_type FROM supply_chain_nodes WHERE asset_ticker = %s",
                (ticker,),
            )
            node = cur.fetchone()
            if not node:
                raise HTTPException(status_code=404, detail=f"Node {ticker} not found")

            cur.execute(
                """
                UPDATE supply_chain_nodes
                   SET extracted_data   = '{}',
                       last_scanned_at  = NOW() - INTERVAL '10 years'
                 WHERE asset_ticker = %s
                """,
                (ticker,),
            )
            conn.commit()
        logger.info(f"Force Refresh: data purged for {ticker}, queuing background analysis")
    except HTTPException:
        raise
    except Exception as exc:
        conn.rollback()
        logger.error(f"Force Refresh purge failed for {ticker}: {exc}")
        raise HTTPException(status_code=500, detail="Failed to purge node data")
    finally:
        release_db_connection(conn)

    company_type = node["company_type"] if node else "PRODUCER"
    background_tasks.add_task(_run_analysis_for_ticker, ticker, company_type)

    return {
        "status": "queued",
        "ticker": ticker,
        "message": f"Data purged and refresh triggered for {ticker}",
    }


__all__ = ["router"]
