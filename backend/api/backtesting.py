"""
Mineral AI Tracker - Backtesting API (PRD v9.0 Phase 3)
Version: 11.0
Description: API endpoints for running and managing backtest simulations
PRD v10.0 Phase 11: Added Celery integration for async backtesting
"""

from typing import Dict, Any, List, Optional
from datetime import datetime, date
from decimal import Decimal
from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends

from api.deps import get_current_user
from pydantic import BaseModel, Field
from loguru import logger
import uuid

import psycopg2
from psycopg2.extras import RealDictCursor, Json

from quant.backtesting import (
    Backtester,
    BacktestConfig,
    run_historical_simulation_pipeline,
)
from ml.slm_orchestrator import SLMOrchestrator
from ml.ollama_client import OllamaClient
from worker.tasks import task_run_backtest

router = APIRouter(prefix="/api/backtesting", tags=["backtesting"])


# ============================================================================
# Pydantic Models
# ============================================================================

class BacktestRequest(BaseModel):
    """Request to run a backtest"""
    strategy_name: str = Field(..., description="Name of the strategy to backtest")
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    initial_capital: float = Field(100000.0, description="Initial capital for backtest")
    tickers: List[str] = Field(..., description="List of tickers to backtest")
    weight_macro: float = Field(0.2, description="Weight for macro factors")
    weight_commodity: float = Field(0.2, description="Weight for commodity factors")
    weight_geo: float = Field(0.2, description="Weight for geopolitical factors")
    weight_insider: float = Field(0.2, description="Weight for insider trading")
    weight_sentiment: float = Field(0.2, description="Weight for sentiment")
    use_half_kelly: bool = Field(True, description="Use half Kelly criterion")
    max_position_size: float = Field(0.25, description="Maximum position size")
    use_real_data: bool = Field(True, description="Use real historical data from yfinance")


class HistoricalSimulationRequest(BaseModel):
    """Request to run historical simulation with AI debate protocol"""
    start_date: str = Field(..., description="Start date (YYYY-MM-DD)")
    end_date: str = Field(..., description="End date (YYYY-MM-DD)")
    tickers: List[str] = Field(..., description="List of tickers to simulate")
    interval_days: int = Field(7, description="Days between snapshots")


class BacktestRunResponse(BaseModel):
    """Response for backtest run"""
    id: str
    strategy_name: str
    start_date: str
    end_date: str
    initial_capital: float
    final_capital: Optional[float]
    total_return_pct: Optional[float]
    sharpe_ratio: Optional[float]
    max_drawdown_pct: Optional[float]
    win_rate: Optional[float]
    trade_count: Optional[int]
    kelly_effectiveness: Optional[Dict[str, Any]]
    created_at: str


# ============================================================================
# Database Helpers
# ============================================================================

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


def ensure_backtest_tables():
    """Ensure backtest tables exist"""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS backtest_runs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    strategy_name VARCHAR(255) NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    initial_capital DECIMAL(15,2) NOT NULL,
                    final_capital DECIMAL(15,2),
                    total_return_pct DECIMAL(10,2),
                    sharpe_ratio DECIMAL(10,4),
                    max_drawdown_pct DECIMAL(10,2),
                    win_rate DECIMAL(5,2),
                    trade_count INTEGER,
                    kelly_effectiveness JSONB,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
                
                CREATE TABLE IF NOT EXISTS backtest_trades (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    backtest_run_id UUID REFERENCES backtest_runs(id) ON DELETE CASCADE,
                    ticker VARCHAR(20) NOT NULL,
                    entry_date DATE NOT NULL,
                    exit_date DATE,
                    entry_price DECIMAL(15,4),
                    exit_price DECIMAL(15,4),
                    shares DECIMAL(15,4),
                    position_size DECIMAL(15,2),
                    ai_recommendation VARCHAR(20),
                    ai_confidence INTEGER,
                    win BOOLEAN,
                    return_pct DECIMAL(10,2),
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
                );
            """)
            conn.commit()
    finally:
        conn.close()


# ============================================================================
# API Endpoints
# ============================================================================

@router.post("/run", response_model=BacktestRunResponse)
async def run_backtest(
    request: BacktestRequest,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Run a backtest simulation (PRD v11.0 Phase 11)
    
    This endpoint triggers a Celery task to run strategy backtesting using historical data.
    Results are stored in the database.
    """
    try:
        user_id = current_user["id"]  # Extract user_id for data isolation
        ensure_backtest_tables()
        
        # Generate backtest ID
        backtest_id = str(uuid.uuid4())
        
        # Prepare weights dictionary
        weights = {
            "macro": request.weight_macro,
            "commodity": request.weight_commodity,
            "geo": request.weight_geo,
            "insider": request.weight_insider,
            "sentiment": request.weight_sentiment
        }
        
        # Trigger Celery task for async backtesting
        task = task_run_backtest.delay(
            strategy_name=request.strategy_name,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            tickers=request.tickers,
            weights=weights,
            use_half_kelly=request.use_half_kelly,
            max_position_size=request.max_position_size,
            use_real_data=request.use_real_data
        )
        
        # Insert initial backtest run record
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO backtest_runs (
                        id, strategy_name, start_date, end_date, initial_capital, user_id
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                """, (
                    backtest_id,
                    request.strategy_name,
                    request.start_date,
                    request.end_date,
                    request.initial_capital,
                    user_id
                ))
                row = cur.fetchone()
                conn.commit()
        finally:
            conn.close()
        
        logger.info(f"Backtest task started: {task.id} for strategy {request.strategy_name}")
        
        return BacktestRunResponse(
            id=backtest_id,
            strategy_name=request.strategy_name,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            final_capital=None,
            total_return_pct=None,
            sharpe_ratio=None,
            max_drawdown_pct=None,
            win_rate=None,
            trade_count=None,
            kelly_effectiveness=None,
            created_at=row['created_at'].isoformat()
        )
    except Exception as e:
        logger.error(f"Backtest run failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs/{run_id}", response_model=BacktestRunResponse)
async def get_backtest_run(
    run_id: str,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """Get details of a specific backtest run"""
    try:
        user_id = current_user["id"]  # Extract user_id for data isolation
        ensure_backtest_tables()
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM backtest_runs WHERE id = %s AND user_id = %s
                """, (run_id, user_id))
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail="Backtest run not found")
                
                return BacktestRunResponse(
                    id=str(row['id']),
                    strategy_name=row['strategy_name'],
                    start_date=row['start_date'].isoformat(),
                    end_date=row['end_date'].isoformat(),
                    initial_capital=float(row['initial_capital']),
                    final_capital=float(row['final_capital']) if row['final_capital'] else None,
                    total_return_pct=float(row['total_return_pct']) if row['total_return_pct'] else None,
                    sharpe_ratio=float(row['sharpe_ratio']) if row['sharpe_ratio'] else None,
                    max_drawdown_pct=float(row['max_drawdown_pct']) if row['max_drawdown_pct'] else None,
                    win_rate=float(row['win_rate']) if row['win_rate'] else None,
                    trade_count=row['trade_count'],
                    kelly_effectiveness=row['kelly_effectiveness'],
                    created_at=row['created_at'].isoformat()
                )
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get backtest run: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/runs")
async def list_backtest_runs(
    limit: int = 50,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """List all backtest runs"""
    try:
        user_id = current_user["id"]  # Extract user_id for data isolation
        ensure_backtest_tables()
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT * FROM backtest_runs
                    WHERE user_id = %s
                    ORDER BY created_at DESC LIMIT %s
                """, (user_id, limit))
                rows = cur.fetchall()
                
                return {
                    "runs": [
                        {
                            "id": str(r['id']),
                            "strategy_name": r['strategy_name'],
                            "start_date": r['start_date'].isoformat(),
                            "end_date": r['end_date'].isoformat(),
                            "initial_capital": float(r['initial_capital']),
                            "final_capital": float(r['final_capital']) if r['final_capital'] else None,
                            "total_return_pct": float(r['total_return_pct']) if r['total_return_pct'] else None,
                            "sharpe_ratio": float(r['sharpe_ratio']) if r['sharpe_ratio'] else None,
                            "max_drawdown_pct": float(r['max_drawdown_pct']) if r['max_drawdown_pct'] else None,
                            "win_rate": float(r['win_rate']) if r['win_rate'] else None,
                            "trade_count": r['trade_count'],
                            "created_at": r['created_at'].isoformat()
                        }
                        for r in rows
                    ],
                    "total": len(rows)
                }
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to list backtest runs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/historical-simulation")
async def run_historical_simulation(
    request: HistoricalSimulationRequest,
    background_tasks: BackgroundTasks,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Run historical simulation with AI debate protocol (PRD v9.0)
    
    This endpoint runs the HistoricalSnapshotter to simulate AI debate runs
    at historical time points, using the SLM Orchestrator.
    
    This runs in the background as it can take significant time.
    """
    try:
        # Initialize orchestrator
        ollama = OllamaClient()
        orchestrator = SLMOrchestrator(ollama)
        
        # Load system settings
        from api.intelligence import load_system_settings_dict
        system_settings = load_system_settings_dict()
        
        # Run simulation in background
        def run_simulation():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(
                    run_historical_simulation_pipeline(
                        start_date=date.fromisoformat(request.start_date),
                        end_date=date.fromisoformat(request.end_date),
                        tickers=request.tickers,
                        slm_orchestrator=orchestrator,
                        system_settings=system_settings
                    )
                )
                logger.info(f"Historical simulation completed: {result['simulations_run']} simulations run")
            finally:
                loop.close()
        
        background_tasks.add_task(run_simulation)
        
        return {
            "status": "started",
            "message": f"Historical simulation started for {len(request.tickers)} tickers from {request.start_date} to {request.end_date}",
            "snapshots_to_analyze": "calculating..."
        }
    except Exception as e:
        logger.error(f"Historical simulation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/trades/{run_id}")
async def get_backtest_trades(
    run_id: str,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """Get all trades for a specific backtest run"""
    try:
        user_id = current_user["id"]  # Extract user_id for data isolation
        ensure_backtest_tables()
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT bt.* FROM backtest_trades bt
                    INNER JOIN backtest_runs br ON bt.backtest_run_id = br.id
                    WHERE bt.backtest_run_id = %s AND br.user_id = %s
                    ORDER BY bt.entry_date
                """, (run_id, user_id))
                rows = cur.fetchall()
                
                return {
                    "trades": [
                        {
                            "id": str(r['id']),
                            "ticker": r['ticker'],
                            "entry_date": r['entry_date'].isoformat(),
                            "exit_date": r['exit_date'].isoformat() if r['exit_date'] else None,
                            "entry_price": float(r['entry_price']),
                            "exit_price": float(r['exit_price']) if r['exit_price'] else None,
                            "shares": float(r['shares']),
                            "position_size": float(r['position_size']),
                            "ai_recommendation": r['ai_recommendation'],
                            "ai_confidence": r['ai_confidence'],
                            "win": r['win'],
                            "return_pct": float(r['return_pct']) if r['return_pct'] else None,
                        }
                        for r in rows
                    ],
                    "total": len(rows)
                }
        finally:
            conn.close()
    except Exception as e:
        logger.error(f"Failed to get backtest trades: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rerun/{run_id}")
async def rerun_backtest(
    run_id: str,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Rerun a backtest with the same configuration (PRD v10.0 Phase 11)
    
    Args:
        run_id: ID of the backtest run to rerun
    
    Returns:
        New backtest run response
    """
    try:
        user_id = current_user["id"]  # Extract user_id for data isolation
        ensure_backtest_tables()
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT strategy_name, start_date, end_date, initial_capital
                    FROM backtest_runs
                    WHERE id = %s AND user_id = %s
                """, (run_id, user_id))
                row = cur.fetchone()
                
                if not row:
                    raise HTTPException(status_code=404, detail="Backtest run not found")
                
                # Create new backtest request from existing configuration
                from worker.tasks import task_run_backtest
                
                new_backtest_id = str(uuid.uuid4())
                
                # Trigger Celery task with same configuration
                # Note: Would need to fetch historical data separately
                task = task_run_backtest.delay(
                    strategy_name=row['strategy_name'],
                    start_date=row['start_date'].isoformat(),
                    end_date=row['end_date'].isoformat(),
                    initial_capital=float(row['initial_capital']),
                    tickers=[],  # Would need to fetch from original config
                    weights={"macro": 0.2, "commodity": 0.2, "geo": 0.2, "insider": 0.2, "sentiment": 0.2},
                    use_half_kelly=True,
                    max_position_size=0.25,
                    use_real_data=True
                )
                
                # Insert new backtest run record
                cur.execute("""
                    INSERT INTO backtest_runs (
                        id, strategy_name, start_date, end_date, initial_capital, user_id
                    ) VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING id, created_at
                """, (
                    new_backtest_id,
                    row['strategy_name'],
                    row['start_date'],
                    row['end_date'],
                    row['initial_capital'],
                    user_id
                ))
                new_row = cur.fetchone()
                conn.commit()
                
                logger.info(f"Backtest rerun started: {task.id} for strategy {row['strategy_name']}")
                
                return BacktestRunResponse(
                    id=new_backtest_id,
                    strategy_name=row['strategy_name'],
                    start_date=row['start_date'].isoformat(),
                    end_date=row['end_date'].isoformat(),
                    initial_capital=float(row['initial_capital']),
                    final_capital=None,
                    total_return_pct=None,
                    sharpe_ratio=None,
                    max_drawdown_pct=None,
                    win_rate=None,
                    trade_count=None,
                    kelly_effectiveness=None,
                    created_at=new_row['created_at'].isoformat()
                )
        finally:
            conn.close()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to rerun backtest: {e}")
        raise HTTPException(status_code=500, detail=str(e))


__all__ = ["router"]
