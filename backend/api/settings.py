"""
Mineral AI Tracker - Settings API (PRD v8.0)
Version: 8.0
Description: API endpoint for system settings and thresholds
"""

import json
from datetime import datetime, timezone

import httpx
from fastapi import APIRouter, HTTPException, Depends

from api.deps import get_current_user
from pydantic import BaseModel
from typing import Any, Dict, Optional
import os
from loguru import logger

# Import models
from models.finance import SystemSettings
from config import settings
from utils.vault import encrypt, decrypt, CRYPTO_AVAILABLE
from utils.database import get_db_connection, release_db_connection
from psycopg2.extras import RealDictCursor

router = APIRouter(prefix="/api/settings", tags=["settings"])


# ============================================================================
# Pydantic Models
# ============================================================================

class SettingsUpdateRequest(BaseModel):
    """Request model for updating settings"""
    max_pe_ratio: Optional[float] = None
    min_market_cap_m: Optional[float] = None
    min_daily_volume_k: Optional[float] = None
    min_confidence_score: Optional[int] = None
    max_geological_grade_copper: Optional[float] = None


class VaultUpdateRequest(BaseModel):
    """Request model for updating vault keys"""
    fmp_api_key: Optional[str] = None


class VaultResponse(BaseModel):
    """Response model for vault status"""
    fmp_api_key_set: bool
    encryption_available: bool
    source: str  # "vault", "env_var", "none"


class SettingsResponse(BaseModel):
    """Response model for settings"""
    max_pe_ratio: float
    min_market_cap_m: float
    min_daily_volume_k: float
    min_confidence_score: int
    max_geological_grade_copper: float
    database_type: str
    ollama_url: str
    ollama_phi3_model: str
    ollama_mistral_model: str
    ollama_llama3_model: str
    fmp_api_key_set: bool = False  # Indicates if vault key is configured


# ============================================================================
# Database Helper Functions
# ============================================================================


def load_settings_from_db() -> Optional[SystemSettings]:
    """Load settings from database (including vault keys if present)"""
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Try to load with vault column first
                try:
                    cur.execute("""
                        SELECT max_pe_ratio, min_market_cap_m, min_daily_volume_k,
                               min_confidence_score, max_geological_grade_copper,
                               fmp_api_key
                        FROM system_settings
                        LIMIT 1
                    """)
                except Exception:
                    # Column doesn't exist yet (pre-9.5 schema)
                    conn.rollback()
                    cur.execute("""
                        SELECT max_pe_ratio, min_market_cap_m, min_daily_volume_k,
                               min_confidence_score, max_geological_grade_copper
                        FROM system_settings
                        LIMIT 1
                    """)
                result = cur.fetchone()

                if result:
                    return SystemSettings(**result)
                return None
        finally:
            release_db_connection(conn)
    except Exception as e:
        logger.warning(f"Failed to load settings from DB: {e}")
        return None


def save_settings_to_db(settings_obj: SystemSettings) -> bool:
    """Save settings to database (including vault keys if present)"""
    try:
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                # Check if settings table exists and has data
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'system_settings'
                    )
                """)
                table_exists = cur.fetchone()[0]

                if not table_exists:
                    # Create settings table
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS system_settings (
                            id SERIAL PRIMARY KEY,
                            max_pe_ratio FLOAT DEFAULT 25.0,
                            min_market_cap_m FLOAT DEFAULT 10.0,
                            min_daily_volume_k FLOAT DEFAULT 500.0,
                            min_confidence_score INTEGER DEFAULT 85,
                            max_geological_grade_copper FLOAT DEFAULT 15.0,
                            fmp_api_key TEXT,
                            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                        )
                    """)
                    conn.commit()

                # Check if vault column exists
                cur.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns
                        WHERE table_name = 'system_settings' AND column_name = 'fmp_api_key'
                    )
                """)
                vault_column_exists = cur.fetchone()[0]

                # Check if settings exist
                cur.execute("SELECT COUNT(*) FROM system_settings")
                count = cur.fetchone()[0]

                if count > 0:
                    # Update existing settings
                    if vault_column_exists:
                        cur.execute("""
                            UPDATE system_settings
                            SET max_pe_ratio = %s,
                                min_market_cap_m = %s,
                                min_daily_volume_k = %s,
                                min_confidence_score = %s,
                                max_geological_grade_copper = %s,
                                fmp_api_key = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = 1
                        """, (
                            settings_obj.max_pe_ratio,
                            settings_obj.min_market_cap_m,
                            settings_obj.min_daily_volume_k,
                            settings_obj.min_confidence_score,
                            settings_obj.max_geological_grade_copper,
                            settings_obj.fmp_api_key,
                        ))
                    else:
                        cur.execute("""
                            UPDATE system_settings
                            SET max_pe_ratio = %s,
                                min_market_cap_m = %s,
                                min_daily_volume_k = %s,
                                min_confidence_score = %s,
                                max_geological_grade_copper = %s,
                                updated_at = CURRENT_TIMESTAMP
                            WHERE id = 1
                        """, (
                            settings_obj.max_pe_ratio,
                            settings_obj.min_market_cap_m,
                            settings_obj.min_daily_volume_k,
                            settings_obj.min_confidence_score,
                            settings_obj.max_geological_grade_copper,
                        ))
                else:
                    # Insert new settings
                    if vault_column_exists:
                        cur.execute("""
                            INSERT INTO system_settings
                            (max_pe_ratio, min_market_cap_m, min_daily_volume_k,
                             min_confidence_score, max_geological_grade_copper, fmp_api_key)
                            VALUES (%s, %s, %s, %s, %s, %s)
                        """, (
                            settings_obj.max_pe_ratio,
                            settings_obj.min_market_cap_m,
                            settings_obj.min_daily_volume_k,
                            settings_obj.min_confidence_score,
                            settings_obj.max_geological_grade_copper,
                            settings_obj.fmp_api_key,
                        ))
                    else:
                        cur.execute("""
                            INSERT INTO system_settings
                            (max_pe_ratio, min_market_cap_m, min_daily_volume_k,
                             min_confidence_score, max_geological_grade_copper)
                            VALUES (%s, %s, %s, %s, %s)
                        """, (
                            settings_obj.max_pe_ratio,
                            settings_obj.min_market_cap_m,
                            settings_obj.min_daily_volume_k,
                            settings_obj.min_confidence_score,
                            settings_obj.max_geological_grade_copper,
                        ))

                conn.commit()
                return True
        finally:
            release_db_connection(conn)
    except Exception as e:
        logger.error(f"Failed to save settings to DB: {e}")
        return False


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("", response_model=SettingsResponse)
async def get_settings(
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get current system settings

    Returns global thresholds and system configuration.
    """
    try:
        # Try to load from database first
        db_settings = load_settings_from_db()

        if db_settings:
            current_settings = db_settings
        else:
            # Use default settings
            current_settings = SystemSettings()

        # Determine vault status
        vault_key_set = bool(current_settings.fmp_api_key)
        if not vault_key_set:
            vault_key_set = bool(settings.FMP_API_KEY)

        return SettingsResponse(
            max_pe_ratio=current_settings.max_pe_ratio,
            min_market_cap_m=current_settings.min_market_cap_m,
            min_daily_volume_k=current_settings.min_daily_volume_k,
            min_confidence_score=current_settings.min_confidence_score,
            max_geological_grade_copper=current_settings.max_geological_grade_copper,
            database_type=settings.DATABASE_TYPE,
            ollama_url=settings.OLLAMA_URL,
            ollama_phi3_model=settings.OLLAMA_PHI3_MODEL,
            ollama_mistral_model=settings.OLLAMA_MISTRAL_MODEL,
            ollama_llama3_model=settings.OLLAMA_LLAMA3_MODEL,
            fmp_api_key_set=vault_key_set,
        )
    except Exception as e:
        logger.error(f"Error getting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("", response_model=SettingsResponse)
async def update_settings(
    request: SettingsUpdateRequest,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Update system settings
    
    Allows user to adjust global thresholds for investment protection.
    """
    try:
        # Load current settings
        db_settings = load_settings_from_db()
        
        if db_settings:
            current_settings = db_settings
        else:
            current_settings = SystemSettings()
        
        # Update only provided fields
        update_data = request.model_dump(exclude_unset=True)
        
        for field, value in update_data.items():
            if hasattr(current_settings, field):
                setattr(current_settings, field, value)
        
        # Save to database
        if not save_settings_to_db(current_settings):
            logger.warning("Failed to save settings to DB, using in-memory")
        
        return SettingsResponse(
            max_pe_ratio=current_settings.max_pe_ratio,
            min_market_cap_m=current_settings.min_market_cap_m,
            min_daily_volume_k=current_settings.min_daily_volume_k,
            min_confidence_score=current_settings.min_confidence_score,
            max_geological_grade_copper=current_settings.max_geological_grade_copper,
            database_type=settings.DATABASE_TYPE,
            ollama_url=settings.OLLAMA_URL,
            ollama_phi3_model=settings.OLLAMA_PHI3_MODEL,
            ollama_mistral_model=settings.OLLAMA_MISTRAL_MODEL,
            ollama_llama3_model=settings.OLLAMA_LLAMA3_MODEL
        )
    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/reset", response_model=SettingsResponse)
async def reset_settings(
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Reset settings to default values

    Restores all thresholds to PRD v8.0 default values.
    """
    try:
        default_settings = SystemSettings()

        # Save to database
        if not save_settings_to_db(default_settings):
            logger.warning("Failed to save settings to DB, using in-memory")

        return SettingsResponse(
            max_pe_ratio=default_settings.max_pe_ratio,
            min_market_cap_m=default_settings.min_market_cap_m,
            min_daily_volume_k=default_settings.min_daily_volume_k,
            min_confidence_score=default_settings.min_confidence_score,
            max_geological_grade_copper=default_settings.max_geological_grade_copper,
            database_type=settings.DATABASE_TYPE,
            ollama_url=settings.OLLAMA_URL,
            ollama_phi3_model=settings.OLLAMA_PHI3_MODEL,
            ollama_mistral_model=settings.OLLAMA_MISTRAL_MODEL,
            ollama_llama3_model=settings.OLLAMA_LLAMA3_MODEL,
            fmp_api_key_set=bool(settings.FMP_API_KEY),
        )
    except Exception as e:
        logger.error(f"Error resetting settings: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# Vault Endpoints (PRD v8.7 Phase 9)
# ============================================================================

@router.get("/vault", response_model=VaultResponse)
async def get_vault_status(
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Get vault status for API keys

    Returns which keys are configured and where they come from (vault vs env var).
    """
    try:
        db_settings = load_settings_from_db()
        vault_key_set = bool(db_settings.fmp_api_key) if db_settings else False
        env_var_set = bool(settings.FMP_API_KEY)

        # Determine active source
        if vault_key_set:
            source = "vault"
        elif env_var_set:
            source = "env_var"
        else:
            source = "none"

        return VaultResponse(
            fmp_api_key_set=vault_key_set or env_var_set,
            encryption_available=CRYPTO_AVAILABLE,
            source=source,
        )
    except Exception as e:
        logger.error(f"Error getting vault status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/vault", response_model=VaultResponse)
async def update_vault(
    request: VaultUpdateRequest,
    current_user: dict = Depends(get_current_user)  # Critical Hotfix: Require authentication
):
    """
    Update vault keys (encrypted at rest)

    Stores the provided API keys encrypted in the database.
    To remove a key, pass an empty string.
    """
    try:
        if request.fmp_api_key is not None:
            # Encrypt the key before storing
            if request.fmp_api_key == "":
                encrypted_key = None  # Remove key
            else:
                encrypted_key = encrypt(request.fmp_api_key)

            # Load current settings
            db_settings = load_settings_from_db()
            if not db_settings:
                db_settings = SystemSettings()

            # Update the vault key
            db_settings.fmp_api_key = encrypted_key

            # Save to database
            if not save_settings_to_db(db_settings):
                raise HTTPException(status_code=500, detail="Failed to save vault key to database")

            logger.info("Vault FMP API key updated")

        # Determine active source after update
        vault_key_set = bool(db_settings.fmp_api_key) if db_settings else False
        env_var_set = bool(settings.FMP_API_KEY)

        if vault_key_set:
            source = "vault"
        elif env_var_set:
            source = "env_var"
        else:
            source = "none"

        return VaultResponse(
            fmp_api_key_set=vault_key_set or env_var_set,
            encryption_available=CRYPTO_AVAILABLE,
            source=source,
        )
    except Exception as e:
        logger.error(f"Error updating vault: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------------
# Notification Routing — Sprint 10.8
# ---------------------------------------------------------------------------

_DEFAULT_NOTIFICATION_PREFS: Dict[str, Any] = {
    "dilution_risk":   {"email": True,  "in_app": True,  "webhook": False},
    "black_swan":      {"email": False, "in_app": True,  "webhook": False},
    "take_or_pay_new": {"email": False, "in_app": True,  "webhook": False},
}


class NotificationPreferences(BaseModel):
    dilution_risk:   Optional[Dict[str, bool]] = None
    black_swan:      Optional[Dict[str, bool]] = None
    take_or_pay_new: Optional[Dict[str, bool]] = None


def _ensure_alert_config_row(user_id: str) -> None:
    """Create an alert_configs row with defaults if one does not exist yet."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO alert_configs (user_id, notification_preferences)
                VALUES (%s, %s::JSONB)
                ON CONFLICT (user_id) DO NOTHING
                """,
                (user_id, json.dumps(_DEFAULT_NOTIFICATION_PREFS)),
            )
            conn.commit()
    except Exception:
        conn.rollback()
    finally:
        release_db_connection(conn)


@router.get("/notifications", response_model=Dict[str, Any])
async def get_notification_preferences(
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Return the current user's notification routing preferences."""
    user_id = current_user.get("sub") or current_user.get("id", "default")
    _ensure_alert_config_row(user_id)

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT notification_preferences FROM alert_configs WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            prefs = row["notification_preferences"] if row else _DEFAULT_NOTIFICATION_PREFS
            if isinstance(prefs, str):
                prefs = json.loads(prefs)
            return prefs
    except Exception as exc:
        logger.error(f"get_notification_preferences failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to load preferences")
    finally:
        release_db_connection(conn)


@router.put("/notifications", response_model=Dict[str, Any])
async def update_notification_preferences(
    body: NotificationPreferences,
    current_user: dict = Depends(get_current_user),
) -> Dict[str, Any]:
    """Merge-update the notification routing preferences (only supplied keys overwritten)."""
    user_id = current_user.get("sub") or current_user.get("id", "default")
    _ensure_alert_config_row(user_id)

    updates = {k: v for k, v in body.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(status_code=400, detail="No preferences supplied")

    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # JSONB merge: existing || new (PostgreSQL 9.5+)
            cur.execute(
                """
                UPDATE alert_configs
                   SET notification_preferences = notification_preferences || %s::JSONB
                 WHERE user_id = %s
                RETURNING notification_preferences
                """,
                (json.dumps(updates), user_id),
            )
            row = cur.fetchone()
            conn.commit()
            prefs = row["notification_preferences"] if row else updates
            if isinstance(prefs, str):
                prefs = json.loads(prefs)
            return prefs
    except Exception as exc:
        conn.rollback()
        logger.error(f"update_notification_preferences failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to update preferences")
    finally:
        release_db_connection(conn)


async def dispatch_risk_alert(
    ticker: str,
    score: float,
    category: str = "dilution_risk",
    user_id: str | None = None,
) -> None:
    """
    Sprint 13 — Alert Subscription Engine.

    Broadcasts to ALL users who have subscribed to `ticker` in `user_alerts`
    with `risk_threshold <= score`.  Reads each user's `notification_preferences`
    and routes to the enabled channels.

    `user_id` is kept as an optional parameter for backward-compat; when omitted
    the function queries `user_alerts` and dispatches to all matching subscribers.
    When supplied it broadcasts only to that single user (direct call path).
    """
    # -- 1. Resolve the list of target users ---------------------------------
    subscribers: list[dict] = []
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            if user_id:
                # Backward-compat: single-user direct call
                cur.execute(
                    "SELECT %s::VARCHAR AS user_id, 0 AS risk_threshold",
                    (user_id,),
                )
            else:
                cur.execute(
                    """
                    SELECT user_id, risk_threshold
                      FROM user_alerts
                     WHERE ticker = %s
                       AND risk_threshold <= %s
                    """,
                    (ticker, int(score)),
                )
            subscribers = [dict(r) for r in cur.fetchall()]
    except Exception as exc:
        logger.warning(f"dispatch_risk_alert: failed to query user_alerts for {ticker}: {exc}")
    finally:
        release_db_connection(conn)

    if not subscribers:
        logger.debug(f"dispatch_risk_alert [{ticker}] score={score:.0f} — no matching subscribers")
        return

    logger.info(
        f"dispatch_risk_alert [{ticker}] score={score:.0f} "
        f"— dispatching to {len(subscribers)} subscriber(s)"
    )

    # -- 2. Dispatch per subscriber ------------------------------------------
    for sub in subscribers:
        await _dispatch_to_user(ticker, score, sub["user_id"], category)


_WEBHOOK_TIMEOUT = 5.0

_CATEGORY_MSG: dict[str, str] = {
    "dilution_risk":   "Dilution Risk: {score:.0f}% (threshold exceeded)",
    "ma_radar":        "M&A Target Score: {score:.0f}% — potential buyout candidate",
    "chokepoint":      "Chokepoint Friction: {score:.0f}% geopolitical cost spike",
    "early_sentiment": "Labor Unrest Signal: confidence {score:.0f}%",
}


async def _send_webhook(
    webhook_url: str,
    alert_type: str,
    ticker: str,
    score: float,
    message: str,
) -> None:
    """POST a structured JSON alert to a user-configured generic webhook.

    Compatible with Slack incoming webhooks, n8n, Make, Zapier, Teams,
    or any HTTP POST endpoint. A broken webhook NEVER raises — it only logs.
    """
    payload = {
        "app": "Mineral AI Tracker",
        "alert_type": alert_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "message": message,
        "meta": {
            "ticker": ticker,
            "score": round(score, 2),
            "alert_type": alert_type,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=_WEBHOOK_TIMEOUT) as client:
            resp = await client.post(webhook_url, json=payload)
            resp.raise_for_status()
            logger.info(
                f"_send_webhook [{alert_type}/{ticker}] → {webhook_url} [{resp.status_code}]"
            )
    except httpx.HTTPStatusError as exc:
        logger.error(
            f"_send_webhook HTTP {exc.response.status_code} for {ticker}/{alert_type} "
            f"at {webhook_url}: {exc}"
        )
    except httpx.RequestError as exc:
        logger.error(
            f"_send_webhook request error for {ticker}/{alert_type} at {webhook_url}: {exc}"
        )


async def _dispatch_to_user(
    ticker: str,
    score: float,
    user_id: str,
    category: str,
) -> None:
    """Load one user's notification_preferences and route the alert."""
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT notification_preferences FROM alert_configs WHERE user_id = %s",
                (user_id,),
            )
            row = cur.fetchone()
            prefs_raw = row["notification_preferences"] if row else _DEFAULT_NOTIFICATION_PREFS
            prefs = prefs_raw if isinstance(prefs_raw, dict) else json.loads(prefs_raw)
    except Exception as exc:
        logger.warning(f"_dispatch_to_user: failed to load prefs for {user_id}: {exc}")
        prefs = _DEFAULT_NOTIFICATION_PREFS
    finally:
        release_db_connection(conn)

    channel_cfg = prefs.get(category, {"email": False, "in_app": True, "webhook": False})
    message = "⚠️ {} — ".format(ticker) + _CATEGORY_MSG.get(
        category, "Alert score: {score:.0f}%"
    ).format(score=score)
    logger.info(f"_dispatch_to_user [{ticker}→{user_id}] channels={channel_cfg}")

    if channel_cfg.get("in_app"):
        _save_in_app_alert(ticker, score, message)

    if channel_cfg.get("email"):
        try:
            from notifications.email import send_email_alert
            await send_email_alert(subject=f"Mineral AI: {message}", body=message)
        except Exception as exc:
            logger.warning(f"Email dispatch failed for {ticker}/{user_id}: {exc}")

    if channel_cfg.get("webhook"):
        webhook_url = prefs.get("webhook_url", "").strip()
        if webhook_url:
            await _send_webhook(
                webhook_url=webhook_url,
                alert_type=category,
                ticker=ticker,
                score=score,
                message=message,
            )
        else:
            logger.debug(
                f"Webhook enabled for {ticker}/{user_id} but no webhook_url in notification_preferences"
            )


# ---------------------------------------------------------------------------
# Alert Subscriptions CRUD \u2014 Sprint 13 (Q2)
# ---------------------------------------------------------------------------

class AlertSubscriptionBody(BaseModel):
    ticker: str
    risk_threshold: int = 75


@router.get("/alerts/subscriptions", response_model=list)
async def list_alert_subscriptions(
    current_user: dict = Depends(get_current_user),
) -> list:
    """List all ticker subscriptions for the current user."""
    user_id = current_user.get("sub") or current_user.get("id", "default")
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT id, ticker, risk_threshold, created_at FROM user_alerts WHERE user_id = %s ORDER BY created_at DESC",
                (user_id,),
            )
            rows = cur.fetchall()
            return [
                {
                    "id": str(r["id"]),
                    "ticker": r["ticker"],
                    "risk_threshold": r["risk_threshold"],
                    "created_at": r["created_at"].isoformat() if r["created_at"] else None,
                }
                for r in rows
            ]
    except Exception as exc:
        logger.error(f"list_alert_subscriptions failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to load subscriptions")
    finally:
        release_db_connection(conn)


@router.post("/alerts/subscriptions", response_model=dict, status_code=201)
async def upsert_alert_subscription(
    body: AlertSubscriptionBody,
    current_user: dict = Depends(get_current_user),
) -> dict:
    """Create or update an alert subscription for a ticker."""
    user_id = current_user.get("sub") or current_user.get("id", "default")
    ticker = body.ticker.upper()
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                """
                INSERT INTO user_alerts (user_id, ticker, risk_threshold)
                VALUES (%s, %s, %s)
                ON CONFLICT (user_id, ticker)
                DO UPDATE SET risk_threshold = EXCLUDED.risk_threshold,
                              updated_at = NOW()
                RETURNING id, ticker, risk_threshold
                """,
                (user_id, ticker, body.risk_threshold),
            )
            row = cur.fetchone()
            conn.commit()
            return {"id": str(row["id"]), "ticker": row["ticker"], "risk_threshold": row["risk_threshold"]}
    except Exception as exc:
        conn.rollback()
        logger.error(f"upsert_alert_subscription failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to save subscription")
    finally:
        release_db_connection(conn)


@router.delete("/alerts/subscriptions/{ticker}", status_code=204)
async def delete_alert_subscription(
    ticker: str,
    current_user: dict = Depends(get_current_user),
) -> None:
    """Remove an alert subscription for a ticker."""
    user_id = current_user.get("sub") or current_user.get("id", "default")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM user_alerts WHERE user_id = %s AND ticker = %s",
                (user_id, ticker.upper()),
            )
            conn.commit()
    except Exception as exc:
        conn.rollback()
        logger.error(f"delete_alert_subscription failed: {exc}")
        raise HTTPException(status_code=500, detail="Failed to delete subscription")
    finally:
        release_db_connection(conn)


def _save_in_app_alert(ticker: str, score: float, message: str) -> None:
    """Persist in-app alert to the alerts table."""
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO alerts (ticker, alert_type, message, triggered_at)
                VALUES (%s, 'DILUTION_RISK', %s, NOW())
                ON CONFLICT DO NOTHING
                """,
                (ticker, message),
            )
            conn.commit()
    except Exception as exc:
        logger.warning(f"_save_in_app_alert failed for {ticker}: {exc}")
        conn.rollback()
    finally:
        release_db_connection(conn)
