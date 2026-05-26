"""
Mineral AI Tracker - Authentication Dependencies (Phase 11/12 Consolidation)
Purpose: JWT authentication validation for FastAPI routers
Date: 2026-05-15
Updated: 2026-05-16 - Replaced placeholder with real HS256 JWT validation via python-jose.
"""

import os
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError, ExpiredSignatureError
from loguru import logger
from psycopg2.extras import RealDictCursor
from utils.database import get_db_connection, release_db_connection

security = HTTPBearer()

# JWT secret - must match NEXTAUTH_SECRET on the frontend so issued tokens validate.
# Production deployments MUST set NEXTAUTH_SECRET; missing secret in production is a
# fatal startup error to prevent shipping with a guessable fallback.
_NEXTAUTH_SECRET = os.getenv("NEXTAUTH_SECRET")
_ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()

if not _NEXTAUTH_SECRET:
    if _ENVIRONMENT == "production":
        raise RuntimeError(
            "FATAL: NEXTAUTH_SECRET is not set in production. "
            "Generate one with `openssl rand -base64 32` and configure it identically "
            "on the Next.js server and the FastAPI backend."
        )
    logger.warning(
        "NEXTAUTH_SECRET is not set - using insecure dev fallback. "
        "This MUST NOT happen in production (set ENVIRONMENT=production to enforce)."
    )
    _NEXTAUTH_SECRET = "dev-insecure-secret-change-me"

_JWT_ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")
_JWT_AUDIENCE = os.getenv("JWT_AUDIENCE")  # Optional; only enforced when set.


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> dict:
    """
    Validate JWT token and return user information.

    Decodes the HS256-signed JWT issued by NextAuth's `jwt` callback against
    the shared `NEXTAUTH_SECRET`. The token must contain at minimum a `sub`
    claim (the user's UUID). `email` and `name` are extracted when present.

    Args:
        credentials: HTTP Bearer token from Authorization header

    Returns:
        Dict with user information (id, email, name)

    Raises:
        HTTPException 401 if the token is missing, malformed, expired or
        otherwise fails signature validation.
    """
    token = credentials.credentials

    decode_kwargs = {"algorithms": [_JWT_ALGORITHM]}
    if _JWT_AUDIENCE:
        decode_kwargs["audience"] = _JWT_AUDIENCE
    else:
        # NextAuth tokens typically have no `aud` claim - skip audience verification
        # to avoid spurious `InvalidAudienceError`.
        decode_kwargs["options"] = {"verify_aud": False}

    try:
        payload = jwt.decode(token, _NEXTAUTH_SECRET, **decode_kwargs)
    except ExpiredSignatureError:
        logger.info("JWT validation failed: token expired")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError as e:
        logger.warning(f"JWT validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub") or payload.get("id")
    if not user_id:
        logger.warning("JWT payload missing 'sub'/'id' claim")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token missing user identifier",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return {
        "id": user_id,
        "email": payload.get("email"),
        "name": payload.get("name"),
    }


async def get_admin_user(
    current_user: dict = Depends(get_current_user),
) -> dict:
    """
    Require the authenticated user to have is_admin=TRUE in the users table.

    Added in Sprint 18 (migration 0007). Node operators promote a user via:
      UPDATE users SET is_admin = TRUE WHERE email = 'operator@example.com';

    Raises:
        HTTPException 403 if the user exists but is not an admin.
    """
    conn = get_db_connection()
    try:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT is_admin FROM users WHERE id = %s",
                (current_user["id"],),
            )
            row = cur.fetchone()
            if not row or not row.get("is_admin"):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Admin access required",
                )
    finally:
        release_db_connection(conn)
    return current_user


async def get_optional_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(HTTPBearer(auto_error=False))) -> Optional[dict]:
    """
    Optional authentication - returns user if authenticated, None otherwise.
    
    Use this for endpoints that work for both authenticated and unauthenticated users,
    but provide enhanced functionality for authenticated users.
    
    Args:
        credentials: Optional HTTP Bearer token
        
    Returns:
        Dict with user information or None if not authenticated
    """
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None
