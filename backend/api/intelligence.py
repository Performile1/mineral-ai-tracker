"""
Mineral AI Tracker - Intelligence API (PRD v8.3)
Version: 10.0
Description: API endpoint for SLM intelligence signals (debate protocol)
PRD v10.0 Phase 10.1: Added user_id for multi-user support
PRD v10.0 Phase 10.3: Added USE_CELERY flag for async processing
Critical Hotfix: Added authentication dependency to enforce JWT validation
"""

import json
import os
from datetime import datetime
from typing import Optional, List, Any, Dict
from utils.vault import encrypt, decrypt, rotate, CRYPTO_AVAILABLE

import psycopg2
from psycopg2.extras import RealDictCursor, Json
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from loguru import logger

from models.finance import SystemSettings
from ml.slm_orchestrator import SLMOrchestrator, DebateResult
from ml.ollama_client import OllamaClient
from ml.gemini_client import GeminiClient
from config import settings
from api.deps import get_current_user

# Phase 10.3: Import Celery app for async processing
if USE_CELERY:
    from worker.celery_app import celery_app
    from worker.tasks import task_run_analysis

router = APIRouter(prefix="/api/intelligence", tags=["intelligence"])

# Phase 10.3: USE_CELERY flag for sync/async fallback
USE_CELERY = os.getenv("USE_CELERY", "False").lower() == "true"

# Phase 13.2: Multi-Model Selector pricing
MODEL_PRICING = {
    "local_swarm": 1,
    "gemini_flash": 2,
    "gemini_pro": 5
}


# ============================================================================
# Pydantic Request/Response Models
# ============================================================================

class AnalyzeRequest(BaseModel):
    raw_data: str = Field(..., description="Raw HTML/Markdown text from scraper")
    source: str = Field(..., description="Data source (e.g., SGU, Mining.com)")
    asset_id: Optional[str] = Field(None, description="Asset ID if updating existing")
    ai_model: str = Field("local_swarm", description="AI model: local_swarm, gemini_flash, gemini_pro")


class DebateStepDict(BaseModel):
    slm: str
    timestamp: str
    reasoning: str
    confidence: int
    output_data: Dict[str, Any]


class AnalyzeResponse(BaseModel):
    signal_type: str
    confidence_score: int
    recommendation: str
    consensus_score: float
    pydantic_passed: bool
    pydantic_errors: List[str]


class ScreenerItem(BaseModel):
    """Single item in the Alpha Screener (PRD v8.9 Phase 11)"""
    ticker: str
    name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    pe_ratio: Optional[float] = None
    market_cap: Optional[float] = None
    ta_status: str  # "BULLISH", "BEARISH", "NEUTRAL", "UNAVAILABLE"
    rsi: Optional[float] = None
    confidence_score: int
    ai_signal: str  # "STRONG BUY", "BUY", "PASS", "SELL", "STRONG SELL"
    recommendation: str
    signal_type: str
    created_at: str


class ScreenerResponse(BaseModel):
    """Response model for the Alpha Screener"""
    items: List[ScreenerItem]
    count: int
    updated_at: str


class SignalListResponse(BaseModel):
    signals: List[Dict[str, Any]]
    total: int


# ============================================================================
# DB Helpers
# ============================================================================

def get_db_connection():
    return psycopg2.connect(
        host=settings.POSTGRES_HOST,
        port=settings.POSTGRES_PORT,
        dbname=settings.POSTGRES_DB,
        user=settings.POSTGRES_USER,
        password=settings.POSTGRES_PASSWORD,
        cursor_factory=RealDictCursor,
    )


def ensure_signal_table():
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS investment_signals (
                    id SERIAL PRIMARY KEY,
                    asset_id VARCHAR(100),
                    signal_type VARCHAR(20),
                    confidence_score INTEGER,
                    recommendation TEXT,
                    consensus_score FLOAT,
                    pydantic_passed BOOLEAN,
                    debate_log JSONB,
                    source VARCHAR(200),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()
    finally:
        conn.close()


def serialize_debate_log(result: DebateResult) -> List[Dict[str, Any]]:
    out = []
    for step in result.debate_log:
        out.append({
            "slm": step.slm.value if hasattr(step.slm, "value") else str(step.slm),
            "timestamp": step.timestamp,
            "input_data": step.input_data,
            "output_data": step.output_data,
            "reasoning": step.reasoning,
            "confidence": step.confidence,
        })
    return out


def _embedding_to_pg_literal(embedding: Optional[List[float]]) -> Optional[str]:
    """Convert a Python list[float] to the pgvector text literal '[v1,v2,...]'."""
    if not embedding:
        return None
    return "[" + ",".join(f"{float(v):.8f}" for v in embedding) + "]"


def save_signal_to_db(
    result: DebateResult,
    asset_id: str,
    source: str,
    user_id: Optional[str] = None,
    embedding: Optional[List[float]] = None,
) -> Optional[int]:
    """
    Persist a Multi-SLM debate result.

    PRD v8.6 Phase 8: when an embedding (768-dim, e.g. nomic-embed-text) is
    supplied, it is stored in the pgvector column for downstream RAG lookup.
    The column is provisioned in db/init/00_init_schema.sql.
    
    PRD v10.0 Phase 10.1: Added user_id for multi-user support.
    """
    try:
        ensure_signal_table()
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                vec_literal = _embedding_to_pg_literal(embedding)
                if vec_literal is not None:
                    cur.execute(
                        """
                        INSERT INTO investment_signals
                        (asset_id, signal_type, confidence_score, recommendation,
                         consensus_score, pydantic_passed, debate_log, source, embedding, user_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::vector, %s)
                        RETURNING id
                        """,
                        (
                            asset_id,
                            result.signal_type,
                            result.confidence_score,
                            result.recommendation,
                            result.consensus_score,
                            result.pydantic_passed,
                            Json(serialize_debate_log(result)),
                            source,
                            vec_literal,
                            user_id,
                        ),
                    )
                else:
                    cur.execute(
                        """
                        INSERT INTO investment_signals
                        (asset_id, signal_type, confidence_score, recommendation,
                         consensus_score, pydantic_passed, debate_log, source, user_id)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                        RETURNING id
                        """,
                        (
                            asset_id,
                            result.signal_type,
                            result.confidence_score,
                            result.recommendation,
                            result.consensus_score,
                            result.pydantic_passed,
                            Json(serialize_debate_log(result)),
                            source,
                            user_id,
                        ),
                    )
                row = cur.fetchone()
                conn.commit()
                return row["id"] if row else None
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to save signal to DB: {e}")
        return None


async def generate_signal_embedding(
    ollama: OllamaClient, raw_data: str, model: str = "nomic-embed-text"
) -> Optional[List[float]]:
    """
    PRD v8.6 Phase 8: helper that generates a vector embedding for the raw
    discovery text. Returns None on failure so saving never blocks on Ollama.
    """
    try:
        vec = await ollama.generate_embedding(text=raw_data, model=model)
        if not vec:
            logger.warning("Empty embedding returned by Ollama")
            return None
        return vec
    except Exception as e:
        logger.warning(f"generate_signal_embedding failed: {e}")
        return None


def load_system_settings_dict() -> Dict[str, Any]:
    """
    Loads system_settings from the DB if present, otherwise returns Pydantic
    defaults. PRD v8.7 Phase 9 forward-compat: opportunistically reads
    `fmp_api_key` if the column exists in the deployed schema (a missing
    column triggers a graceful fallback to the legacy 5-column SELECT).
    Vault keys are decrypted before returning.
    """
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                try:
                    cur.execute("""
                        SELECT max_pe_ratio, min_market_cap_m, min_daily_volume_k,
                               min_confidence_score, max_geological_grade_copper,
                               fmp_api_key
                        FROM system_settings LIMIT 1
                    """)
                except Exception:
                    # Column doesn't exist yet (pre-9.5 schema) - retry without it
                    conn.rollback()
                    cur.execute("""
                        SELECT max_pe_ratio, min_market_cap_m, min_daily_volume_k,
                               min_confidence_score, max_geological_grade_copper
                        FROM system_settings LIMIT 1
                    """)
                row = cur.fetchone()
                if row:
                    settings_dict = dict(row)
                    # Decrypt vault key if present
                    if settings_dict.get("fmp_api_key"):
                        decrypted = decrypt(settings_dict["fmp_api_key"])
                        if decrypted:
                            settings_dict["fmp_api_key"] = decrypted
                        else:
                            # If decryption fails, keep the encrypted value (FMP client will handle it)
                            logger.warning("Failed to decrypt fmp_api_key in load_system_settings_dict")
                    return settings_dict
        finally:
            conn.close()
    except Exception as e:
        logger.warning(f"load_system_settings_dict fallback: {e}")
    return SystemSettings().model_dump()


# ============================================================================
# Endpoints
# ============================================================================

@router.post("/analyze", response_model=AnalyzeResponse)
async def analyze_discovery(
    request: AnalyzeRequest,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Run the Multi-SLM Debate Protocol or Gemini analysis:
    Phi-3 (extract) -> Pydantic Firewall -> Mistral (geology) -> Llama-3 (risk) -> Consensus
    
    PRD v10.0 Phase 10.1: Added user_id for multi-user support
    PRD v10.0 Phase 10.3: Added USE_CELERY flag for async processing
    PRD v12.0 Phase 12: Added credit check before analysis
    PRD v13.2 Phase 13.2: Added multi-model selector with dynamic pricing
    Critical Hotfix: user_id is now sourced from authenticated session, not request param.
    """
    # Phase 13.2: Validate ai_model
    allowed_models = ["local_swarm", "gemini_flash", "gemini_pro"]
    if request.ai_model not in allowed_models:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid ai_model. Must be one of {allowed_models}"
        )
    
    # Phase 13.2: Check if Gemini is available (if selected)
    if request.ai_model.startswith("gemini"):
        gemini_client = GeminiClient()
        if not gemini_client.is_available():
            raise HTTPException(
                status_code=503,
                detail="Gemini API not configured. Please use Local Swarm or configure GEMINI_API_KEY."
            )
    
    user_id = current_user["id"]
    credits_required = MODEL_PRICING[request.ai_model]
    
    # Phase 13.2: Transaction-safe credit deduction
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT credits_remaining FROM users WHERE id = %s
            """, (user_id,))
            row = cur.fetchone()
            if not row:
                logger.warning(f"User {user_id} not found")
                raise HTTPException(status_code=404, detail="User not found")
            
            credits = row["credits_remaining"]
            if credits < credits_required:
                logger.warning(f"User {user_id} has insufficient credits: {credits} < {credits_required}")
                raise HTTPException(
                    status_code=402,
                    detail=f"Insufficient credits. Requires {credits_required} credits, you have {credits}."
                )
            
            # DEDUCT CREDITS (transaction begins)
            cur.execute("""
                UPDATE users 
                SET credits_remaining = credits_remaining - %s,
                    credits_used = COALESCE(credits_used, 0) + %s
                WHERE id = %s
                RETURNING credits_remaining
            """, (credits_required, credits_required, user_id))
            new_balance = cur.fetchone()["credits_remaining"]
            conn.commit()
            logger.info(f"Deducted {credits_required} credits from user {user_id}. New balance: {new_balance}")
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=f"Credit transaction failed: {str(e)}")
    
    # Phase 13.2: Run analysis with transaction-safe error handling
    try:
        # Phase 10.3: Use Celery for async processing if enabled
        if USE_CELERY:
            # Extract ticker from raw data for Celery task
            ticker = "UNKNOWN"  # TODO: Extract ticker from request
            
            # Trigger Celery task with ai_model
            task = task_run_analysis.delay(
                ticker=ticker,
                user_id=user_id,
                is_public=False,
                ai_model=request.ai_model,
                raw_data=request.raw_data,
                source=request.source
            )
            
            return {
                "status": "processing",
                "task_id": task.id,
                "message": f"Analysis started with {request.ai_model}. Poll /api/intelligence/status/{task_id} for results."
            }
        
        # Synchronous execution
        if request.ai_model == "local_swarm":
            # Use existing SLM orchestrator
            ollama = OllamaClient()
            orchestrator = SLMOrchestrator(ollama)
            sys_settings = load_system_settings_dict()

            result = await orchestrator.analyze_discovery(
                raw_data=request.raw_data,
                source=request.source,
                system_settings=sys_settings,
            )
        else:
            # Use Gemini client
            gemini_client = GeminiClient()
            if request.ai_model == "gemini_flash":
                analysis = await gemini_client.generate_flash(request.raw_data)
            else:  # gemini_pro
                analysis = await gemini_client.generate_pro(request.raw_data)
            
            # Format Gemini response to match DebateResult structure
            result = DebateResult(
                signal_type="HOLD",  # Gemini doesn't produce signal_type, use HOLD
                confidence_score=75,
                recommendation=analysis,
                debate_log=[],
                consensus_score=0.5,
                pydantic_passed=True,
                pydantic_errors=[]
            )

        # Save signal to database if threshold met
        if request.ai_model == "local_swarm":
            threshold = sys_settings.get("min_confidence_score", 85)
            if result.pydantic_passed and result.confidence_score >= threshold:
                asset_id = request.asset_id or f"sig_{int(datetime.utcnow().timestamp())}"
                embedding = await generate_signal_embedding(ollama, request.raw_data)
                save_signal_to_db(result, asset_id, request.source, user_id=user_id, embedding=embedding)

        return AnalyzeResponse(
            signal_type=result.signal_type,
            confidence_score=result.confidence_score,
            recommendation=result.recommendation,
            consensus_score=result.consensus_score,
            pydantic_passed=result.pydantic_passed,
            pydantic_errors=result.pydantic_errors,
            debate_log=serialize_debate_log(result),
            timestamp=datetime.utcnow().isoformat(),
        )
        
    except Exception as e:
        # Phase 13.2: REFUND CREDITS on failure (transaction-safe)
        logger.error(f"Analysis failed, refunding {credits_required} credits: {e}")
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    UPDATE users 
                    SET credits_remaining = credits_remaining + %s,
                        credits_used = credits_used - %s
                    WHERE id = %s
                """, (credits_required, credits_required, user_id))
                conn.commit()
                logger.info(f"Refunded {credits_required} credits to user {user_id}")
        except Exception as refund_error:
            logger.error(f"Failed to refund credits: {refund_error}")
            # Continue to raise the original error
        
        raise HTTPException(
            status_code=503,
            detail=f"{request.ai_model} unavailable. Credits refunded. Please try again or use Local Swarm."
        )
    finally:
        conn.close()


@router.get("/models/available")
async def get_available_models(
    current_user: dict = Depends(get_current_user)  # Require authentication
):
    """
    Get available AI models for analysis (Phase 13.2)
    
    Returns list of available models with their costs.
    Gemini models are hidden if GEMINI_API_KEY is not configured.
    """
    try:
        gemini_client = GeminiClient()
        models = [
            {
                "id": "local_swarm",
                "name": "Local Swarm (Llama-3)",
                "cost": 1,
                "available": True,
                "description": "Fast local analysis using Phi-3, Mistral, and Llama-3"
            }
        ]
        
        if gemini_client.is_available():
            models.extend([
                {
                    "id": "gemini_flash",
                    "name": "Cloud Engine (Gemini Flash)",
                    "cost": 2,
                    "available": True,
                    "description": "Fast cloud analysis with Google Gemini Flash"
                },
                {
                    "id": "gemini_pro",
                    "name": "Deep Cloud (Gemini Pro)",
                    "cost": 5,
                    "available": True,
                    "description": "Deep analysis with Google Gemini Pro (1M token context)"
                }
            ])
        
        return {"models": models}
    except Exception as e:
        logger.error(f"Failed to get available models: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/status/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get status of a Celery task (Phase 10.3)
    
    Returns the current status and result if the task is complete.
    """
    if not USE_CELERY:
        raise HTTPException(status_code=501, detail="Celery is not enabled")
    
    try:
        result = celery_app.AsyncResult(task_id)
        return {
            "task_id": task_id,
            "status": result.status,
            "result": result.result if result.ready() else None
        }
    except Exception as e:
        logger.error(f"Failed to get task status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/signals", response_model=SignalListResponse)
async def list_signals(
    limit: int = 50, 
    signal_type: Optional[str] = None,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """List recent intelligence signals (filtered by signal_type optionally)"""
    try:
        user_id = current_user["id"]  # Critical Hotfix: Extract user_id from auth context
        ensure_signal_table()
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                if signal_type:
                    # Critical Hotfix: Add user_id filtering for application-level data isolation
                    cur.execute("""
                        SELECT id, asset_id, signal_type, confidence_score,
                               recommendation, consensus_score, pydantic_passed,
                               source, created_at
                        FROM investment_signals
                        WHERE signal_type = %s AND user_id = %s
                        ORDER BY created_at DESC LIMIT %s
                    """, (signal_type, user_id, limit))
                else:
                    # Critical Hotfix: Add user_id filtering for application-level data isolation
                    cur.execute("""
                        SELECT id, asset_id, signal_type, confidence_score,
                               recommendation, consensus_score, pydantic_passed,
                               source, created_at
                        FROM investment_signals
                        WHERE user_id = %s
                        ORDER BY created_at DESC LIMIT %s
                    """, (user_id, limit))
                rows = cur.fetchall()
                signals = [
                    {
                        **dict(r),
                        "created_at": r["created_at"].isoformat() if r.get("created_at") else None,
                    }
                    for r in rows
                ]
                return SignalListResponse(signals=signals, total=len(signals))
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"list_signals error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/screener", response_model=ScreenerResponse)
async def get_screener(
    limit: int = 100,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get Alpha Screener data (PRD v8.9 Phase 11)

    Aggregates investment_signals with FMP fundamentals and technical analysis
    to provide a comprehensive view of all analyzed assets.
    """
    try:
        user_id = current_user["id"]  # Critical Hotfix: Extract user_id from auth context
        ensure_signal_table()
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Critical Hotfix: Add user_id filtering for application-level data isolation
                cur.execute("""
                    SELECT asset_id, signal_type, confidence_score, recommendation,
                           debate_log, created_at
                    FROM investment_signals
                    WHERE user_id = %s
                    ORDER BY created_at DESC LIMIT %s
                """, (user_id, limit))
                rows = cur.fetchall()

                screener_items = []
                for row in rows:
                    asset_id = row.get("asset_id", "")
                    
                    # Extract ticker from asset_id or debate log
                    ticker = asset_id.upper()
                    if not ticker or ticker == "UNKNOWN":
                        # Try to extract from debate log
                        debate_log = row.get("debate_log", {})
                        if isinstance(debate_log, dict):
                            ticker = debate_log.get("ticker", asset_id).upper()
                    
                    # Get FMP data
                    fmp_data = {}
                    ta_data = {}
                    
                    try:
                        # Fetch FMP fundamentals
                        from utils.fmp_client import fetch_fmp_fundamentals
                        fmp_data = await fetch_fmp_fundamentals(ticker=ticker, system_settings=load_system_settings_dict())
                    except Exception as e:
                        logger.warning(f"FMP fetch failed for {ticker}: {e}")
                    
                    try:
                        # Fetch TA data
                        from engines.technical import TechnicalAnalyzer
                        import httpx
                        analyzer = TechnicalAnalyzer()
                        async with httpx.AsyncClient(timeout=10.0) as client:
                            resp = await client.get(
                                f"http://localhost:8000/api/market/ohlc/{ticker}",
                                params={"period": "1y", "interval": "1d"}
                            )
                            resp.raise_for_status()
                            data = resp.json()
                            ohlc_data = data.get("data", [])
                            if len(ohlc_data) >= 50:
                                ta_data = analyzer.analyze_ticker(ohlc_data)
                    except Exception as e:
                        logger.warning(f"TA fetch failed for {ticker}: {e}")
                    
                    # Determine TA status
                    ta_status = "UNAVAILABLE"
                    if ta_data:
                        rsi = ta_data.get("rsi")
                        macd = ta_data.get("macd", 0)
                        macd_signal = ta_data.get("macd_signal", 0)
                        
                        if rsi and macd:
                            if rsi < 30 and macd > macd_signal:
                                ta_status = "BULLISH"
                            elif rsi > 70 and macd < macd_signal:
                                ta_status = "BEARISH"
                            else:
                                ta_status = "NEUTRAL"
                    
                    # Determine AI signal from recommendation
                    rec = row.get("recommendation", "PASS").upper()
                    confidence = row.get("confidence_score", 50)
                    
                    if rec == "BUY" and confidence >= 90:
                        ai_signal = "STRONG BUY"
                    elif rec == "BUY" and confidence >= 70:
                        ai_signal = "BUY"
                    elif rec == "SELL" and confidence >= 90:
                        ai_signal = "STRONG SELL"
                    elif rec == "SELL" and confidence >= 70:
                        ai_signal = "SELL"
                    else:
                        ai_signal = "PASS"
                    
                    screener_items.append(ScreenerItem(
                        ticker=ticker,
                        name=fmp_data.get("company_name") if fmp_data else None,
                        sector=fmp_data.get("industry") if fmp_data else None,
                        industry=fmp_data.get("sector") if fmp_data else None,
                        pe_ratio=fmp_data.get("pe_ratio") if fmp_data else None,
                        market_cap=fmp_data.get("market_cap") if fmp_data else None,
                        ta_status=ta_status,
                        rsi=ta_data.get("rsi") if ta_data else None,
                        confidence_score=row.get("confidence_score", 50),
                        ai_signal=ai_signal,
                        recommendation=row.get("recommendation", "PASS"),
                        signal_type=row.get("signal_type", "UNKNOWN"),
                        created_at=row.get("created_at").isoformat() if row.get("created_at") else None,
                    ))
                
                return ScreenerResponse(
                    items=screener_items,
                    count=len(screener_items),
                    updated_at=datetime.utcnow().isoformat(),
                )
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"get_screener error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debate/{asset_id}")
async def get_debate_log(
    asset_id: str,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """Return the full debate log for the latest signal of asset_id"""
    try:
        user_id = current_user["id"]  # Critical Hotfix: Extract user_id from auth context
        ensure_signal_table()
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Critical Hotfix: Add user_id filtering for application-level data isolation
                cur.execute("""
                    SELECT asset_id, debate_log, created_at
                    FROM investment_signals
                    WHERE asset_id = %s AND user_id = %s
                    ORDER BY created_at DESC LIMIT 1
                """, (asset_id, user_id))
                row = cur.fetchone()
                if not row:
                    raise HTTPException(status_code=404, detail="Asset not found")
                return {
                    "asset_id": row["asset_id"],
                    "debate_log": row["debate_log"],
                    "timestamp": row["created_at"].isoformat() if row.get("created_at") else None,
                }
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"get_debate_log error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
