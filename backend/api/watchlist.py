"""
Mineral AI Tracker - Watchlist Stalker API (PRD v8.6)
Version: 10.0
Description: POST /api/watchlist/stalk - on-demand Multi-SLM analysis of a
             user-supplied ticker. Highest system priority - parallel scrape,
             sequential SLM debate.
PRD v10.0 Phase 10.1: Added user_id for multi-user support
PRD v10.0 Phase 10.3: Added Celery async task processing
Critical Hotfix: Added authentication dependency to enforce JWT validation
"""

import asyncio
import os
from datetime import datetime
from typing import Optional, List, Dict, Any

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from loguru import logger

from scrapers.discovery import discover_news
from scrapers.crawler import fetch_markdown
from ml.slm_orchestrator import SLMOrchestrator
from ml.ollama_client import OllamaClient
from api.intelligence import (
    load_system_settings_dict,
    save_signal_to_db,
    serialize_debate_log,
    generate_signal_embedding,
)
from config import settings
from api.deps import get_current_user

router = APIRouter(prefix="/api/watchlist", tags=["watchlist"])


# ============================================================================
# Status Endpoint for Celery Tasks (PRD v10.0 Phase 10.3)
# ============================================================================

class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # PENDING, SUCCESS, FAILURE
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


@router.get("/status/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Check the status of a Celery task (PRD v10.0 Phase 10.3)
    
    Returns the current status (PENDING, SUCCESS, FAILURE) and result if available.
    """
    try:
        from worker.celery_app import celery_app
        result = celery_app.AsyncResult(task_id)
        
        response = TaskStatusResponse(
            task_id=task_id,
            status=result.status,
        )
        
        if result.ready():
            if result.successful():
                response.result = result.result
            elif result.failed():
                response.error = str(result.result)
        
        return response
    except Exception as e:
        logger.error(f"Failed to check task status: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to check task status: {e}")


# A semaphore makes this endpoint the *highest priority* user-facing job:
# at most one Stalker run at a time so it never collides with the 06:00 sweep.
_stalker_lock = asyncio.Lock()


# ============================================================================
# Pydantic models
# ============================================================================

class StalkRequest(BaseModel):
    ticker: str = Field(..., description="Ticker (e.g., 'BOL.ST', 'AAPL')")
    max_articles: int = Field(3, ge=1, le=5, description="Max news articles to crawl")
    ai_model: str = Field("local_swarm", description="AI model: local_swarm, gemini_flash, gemini_pro")


class StalkArticle(BaseModel):
    title: str
    url: str
    pub_date: Optional[str] = None
    summary: Optional[str] = None
    fetched_chars: int = 0


class StalkResponse(BaseModel):
    ticker: str
    articles: List[StalkArticle]
    signal_type: str
    confidence_score: int
    recommendation: str
    consensus_score: float
    pydantic_passed: bool
    pydantic_errors: List[str]
    debate_log: List[Dict[str, Any]]
    elapsed_seconds: float
    timestamp: str
    task_id: Optional[str] = None  # PRD v10.0 Phase 10.3: Celery task ID


# ============================================================================
# Endpoint
# ============================================================================

@router.post("/stalk", response_model=StalkResponse)
async def stalk_ticker(
    request: StalkRequest, 
    user_id: Optional[str] = None, 
    is_public: bool = False,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    On-demand "Watchlist Stalker" - runs the full Multi-SLM pipeline against
    a single ticker.

    Pipeline (5 steps, fronted by the UI):
        1. Discovery (Yahoo RSS) - parallel
        2. Crawl4AI fetch         - PARALLEL across N URLs
        3. Phi-3 extract          - sequential, keep_alive=0
        4. Mistral geology debate - sequential, keep_alive=0
        5. Llama-3 risk debate    - sequential, keep_alive=0
    
    PRD v10.0 Phase 10.3: If USE_CELERY is True, queue task and return task_id.
    Otherwise, run synchronously (current behavior).
    """
    ticker = request.ticker.strip().upper()
    if not ticker:
        raise HTTPException(status_code=400, detail="Empty ticker")

    started = datetime.utcnow()

    # PRD v10.0 Phase 10.3: Use Celery for async processing
    if settings.USE_CELERY:
        try:
            from worker.tasks import task_run_analysis
            # Phase 13.2: Pass ai_model to Celery task
            task = task_run_analysis.delay(
                ticker, 
                user_id, 
                is_public,
                ai_model=request.ai_model  # Phase 13.2
            )
            logger.info(f"Queued async analysis for {ticker} with {request.ai_model} (task_id: {task.id})")
            
            # Return immediate response with task_id
            return StalkResponse(
                ticker=ticker,
                signal_type="PROCESSING",
                confidence_score=0,
                recommendation="Analysis queued",
                consensus_score=0.0,
                pydantic_passed=False,
                pydantic_errors=[],
                debate_log=[],
                elapsed_seconds=0.0,
                timestamp=datetime.utcnow().isoformat(),
                task_id=task.id,
            )
        except Exception as e:
            logger.error(f"Failed to queue Celery task: {e}")
            # Fallback to synchronous if Celery fails
            logger.warning("Falling back to synchronous processing")

    # Synchronous processing (original behavior)
    async with _stalker_lock:
        # ---- STEP 1: Discovery ----
        news_items = await discover_news(ticker, limit=request.max_articles)
        if not news_items:
            raise HTTPException(
                status_code=404,
                detail=f"No recent news found for {ticker} on Yahoo Finance RSS",
            )

        # ---- STEP 2: Parallel Crawl ----
        logger.info(f"🕷  Stalker crawling {len(news_items)} URLs for {ticker}")
        crawl_tasks = [fetch_markdown(item["url"]) for item in news_items]
        markdowns = await asyncio.gather(*crawl_tasks, return_exceptions=True)

        articles: List[StalkArticle] = []
        combined_chunks: List[str] = []
        for item, md in zip(news_items, markdowns):
            content = "" if isinstance(md, Exception) or md is None else str(md)
            articles.append(StalkArticle(
                title=item["title"],
                url=item["url"],
                pub_date=item.get("pub_date"),
                summary=item.get("summary"),
                fetched_chars=len(content),
            ))
            if content:
                # Cap per-article so the SLM prompt stays sane
                combined_chunks.append(
                    f"## {item['title']}\nSource: {item['url']}\n\n{content[:6000]}"
                )

        if not combined_chunks:
            raise HTTPException(
                status_code=502,
                detail=f"All article fetches failed for {ticker}",
            )

        combined_text = "\n\n---\n\n".join(combined_chunks)

        # ---- STEP 3-5: Sequential Multi-SLM Debate ----
        ollama = OllamaClient()
        orchestrator = SLMOrchestrator(ollama)
        sys_settings = load_system_settings_dict()

        result = await orchestrator.analyze_discovery(
            raw_data=combined_text,
            source=f"watchlist_stalker:{ticker}",
            system_settings=sys_settings,
        )

        # Persist only high-confidence signals (same rule as nightly sweep)
        threshold = sys_settings.get("min_confidence_score", 85)
        if result.pydantic_passed and result.confidence_score >= threshold:
            embedding = await generate_signal_embedding(ollama, combined_text)
            save_signal_to_db(
                result,
                asset_id=ticker,
                source=f"stalker:{ticker}",
                user_id=user_id,
                embedding=embedding,
            )

        elapsed = (datetime.utcnow() - started).total_seconds()
        logger.info(
            f"✅ Stalker {ticker}: {result.signal_type} ({result.confidence_score}) "
            f"in {elapsed:.1f}s"
        )

        return StalkResponse(
            ticker=ticker,
            articles=articles,
            signal_type=result.signal_type,
            confidence_score=result.confidence_score,
            recommendation=result.recommendation,
            consensus_score=result.consensus_score,
            pydantic_passed=result.pydantic_passed,
            pydantic_errors=result.pydantic_errors,
            debate_log=serialize_debate_log(result),
            elapsed_seconds=round(elapsed, 2),
            timestamp=datetime.utcnow().isoformat(),
        )


@router.get("/discover/{ticker}")
async def discover_only(
    ticker: str,
    limit: int = 3,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """Lightweight endpoint: just the RSS lookup, no crawl/SLM. For previewing."""
    items = await discover_news(ticker, limit=limit)
    return {"ticker": ticker.upper(), "items": items, "count": len(items)}
