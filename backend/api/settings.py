"""
Mineral AI Tracker - Settings API (PRD v8.0)
Version: 8.0
Description: API endpoint for system settings and thresholds
"""

from fastapi import APIRouter, HTTPException, Depends

from api.deps import get_current_user
from pydantic import BaseModel
from typing import Optional
import os
from loguru import logger

# Import models
from models.finance import SystemSettings
from config import settings
from utils.vault import encrypt, decrypt, CRYPTO_AVAILABLE

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

def get_db_connection():
    """Get database connection"""
    import psycopg2
    from psycopg2.extras import RealDictCursor
    
    # Use keyword parameters to avoid DSN parsing issues
    return psycopg2.connect(
        host="localhost",
        port=5432,
        database="mineral_ai_tracker",
        user="mineral_user",
        password="mineralpass123",
        cursor_factory=RealDictCursor
    )


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
            conn.close()
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
            conn.close()
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
