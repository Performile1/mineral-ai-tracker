"""
Mineral AI Tracker - Execution Engine (PRD v8.6 §1, Phase 8)
Version: 8.6
Description: POST /api/execution/trade - mock order endpoint that uses the
             Kelly Criterion to recommend a position size and an automatic
             10% stop-loss for a paper-traded buy/sell.
"""

from decimal import Decimal
from datetime import datetime
from typing import Optional, List, Dict, Any
from uuid import uuid4

import httpx
from fastapi import APIRouter, HTTPException, Depends

from api.deps import get_current_user
from pydantic import BaseModel, Field, field_validator
from loguru import logger

from quant.kelly_criterion import KellyCriterionCalculator
from api.market import YAHOO_QUOTE_URL, USER_AGENT, TIMEOUT

router = APIRouter(prefix="/api/execution", tags=["execution"])


# Default risk params - configurable via request
DEFAULT_BANKROLL_SEK = 100_000.0
DEFAULT_RISK_REWARD = 2.0    # 2:1 target/stop
DEFAULT_STOP_LOSS_PCT = 0.10  # 10% below entry


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------

class TradeRequest(BaseModel):
    ticker: str = Field(..., description="Yahoo-style ticker, e.g. BOL.ST")
    action: str = Field("buy", description="'buy' or 'sell'")
    confidence: int = Field(..., ge=0, le=100, description="AI confidence 0-100")
    bankroll: float = Field(DEFAULT_BANKROLL_SEK, gt=0)
    risk_reward_ratio: float = Field(DEFAULT_RISK_REWARD, gt=0)
    stop_loss_pct: float = Field(DEFAULT_STOP_LOSS_PCT, gt=0, lt=1)
    use_half_kelly: bool = True

    @field_validator("action")
    @classmethod
    def _norm_action(cls, v: str) -> str:
        v = v.lower().strip()
        if v not in {"buy", "sell"}:
            raise ValueError("action must be 'buy' or 'sell'")
        return v


class TradeResponse(BaseModel):
    order_id: str
    ticker: str
    action: str
    entry_price: float
    currency: Optional[str] = None
    suggested_size_sek: float
    suggested_size_pct: float
    suggested_shares: int
    stop_loss_price: float
    take_profit_price: float
    kelly_fraction: float
    kelly_interpretation: str
    expected_value: float
    confidence: int
    reasoning: str
    executed_at: str


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _fetch_live_price(ticker: str) -> Dict[str, Any]:
    """Reuse Yahoo proxy logic from api.market - returns price + currency."""
    async with httpx.AsyncClient(timeout=TIMEOUT, follow_redirects=True) as client:
        resp = await client.get(
            YAHOO_QUOTE_URL,
            params={"symbols": ticker},
            headers={"User-Agent": USER_AGENT},
        )
        resp.raise_for_status()
        data = resp.json()
    items = (data.get("quoteResponse") or {}).get("result") or []
    if not items or items[0].get("regularMarketPrice") is None:
        raise HTTPException(status_code=404, detail=f"No live price for {ticker}")
    item = items[0]
    return {
        "price": float(item["regularMarketPrice"]),
        "currency": item.get("currency"),
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/trade", response_model=TradeResponse)
async def submit_trade(
    req: TradeRequest,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
) -> TradeResponse:
    """
    Mock execution: takes (ticker, action, confidence) and returns:
      - Kelly-sized position (SEK + share count)
      - Auto stop-loss (default -10%)
      - Take-profit at risk_reward_ratio × stop distance

    No real order is placed - this drives the Shadow Portfolio.
    """
    quote = await _fetch_live_price(req.ticker)
    entry_price = quote["price"]

    # Convert AI confidence (0-100) to win probability (clamped 0.05..0.95)
    win_prob = max(0.05, min(0.95, req.confidence / 100.0))

    kelly = KellyCriterionCalculator(use_half_kelly=req.use_half_kelly)
    kelly_result = kelly.calculate_position_size(
        win_probability=Decimal(str(win_prob)),
        risk_reward_ratio=Decimal(str(req.risk_reward_ratio)),
    )
    fraction = float(kelly_result["kelly_position_size"])
    suggested_size_sek = fraction * req.bankroll
    suggested_shares = int(suggested_size_sek // entry_price) if entry_price > 0 else 0

    # Risk levels
    if req.action == "buy":
        stop_loss_price = round(entry_price * (1 - req.stop_loss_pct), 4)
        take_profit_price = round(
            entry_price * (1 + req.stop_loss_pct * req.risk_reward_ratio), 4
        )
    else:  # sell / short
        stop_loss_price = round(entry_price * (1 + req.stop_loss_pct), 4)
        take_profit_price = round(
            entry_price * (1 - req.stop_loss_pct * req.risk_reward_ratio), 4
        )

    order_id = str(uuid4())
    reasoning = (
        f"Kelly {fraction * 100:.2f}% of {req.bankroll:,.0f} SEK "
        f"({kelly_result['interpretation']}, half-Kelly={req.use_half_kelly}). "
        f"Auto stop-loss {req.stop_loss_pct * 100:.0f}% -> {stop_loss_price}. "
        f"Take-profit at {req.risk_reward_ratio:.1f}R -> {take_profit_price}."
    )

    logger.info(
        f"📑 Mock trade {order_id[:8]} {req.action.upper()} {req.ticker} "
        f"@{entry_price} size={suggested_size_sek:,.0f} stop={stop_loss_price}"
    )

    return TradeResponse(
        order_id=order_id,
        ticker=req.ticker.upper(),
        action=req.action,
        entry_price=entry_price,
        currency=quote.get("currency"),
        suggested_size_sek=round(suggested_size_sek, 2),
        suggested_size_pct=round(fraction * 100, 2),
        suggested_shares=suggested_shares,
        stop_loss_price=stop_loss_price,
        take_profit_price=take_profit_price,
        kelly_fraction=fraction,
        kelly_interpretation=kelly_result["interpretation"],
        expected_value=float(kelly_result["expected_value"]),
        confidence=req.confidence,
        reasoning=reasoning,
        executed_at=datetime.utcnow().isoformat(),
    )


@router.post("/preview", response_model=TradeResponse)
async def preview_trade(
    req: TradeRequest,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
) -> TradeResponse:
    """Alias for /trade - kept for UIs that want a 'dry-run' verb."""
    return await submit_trade(req, current_user)
