"""
Mineral AI Tracker - API Credential Vault (PRD v8.7 Phase 9)
Version: 8.7
Description: AES-GCM encryption for storing API keys securely in the database.

Keys are encrypted at rest using a master key derived from:
  1. VAULT_MASTER_KEY env var (preferred for production)
  2. A deterministic fallback from DATABASE_PASSWORD (dev only)

Encrypted format: base64(nonce || ciphertext || tag) for single-column storage.
"""

import os
import base64
from typing import Optional, Tuple
from loguru import logger

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    from cryptography.hazmat.backends import default_backend
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False
    logger.warning("cryptography library not installed - vault will use base64 encoding only (INSECURE)")

# Constants
NONCE_SIZE = 12  # 96 bits for GCM
KEY_SIZE = 32    # 256 bits for AES-256


def _derive_master_key() -> bytes:
    """
    Derive a 256-bit master key from environment variables.
    
    Priority:
      1. VAULT_MASTER_KEY (hex or base64 encoded)
      2. Fallback: hash of DATABASE_PASSWORD (dev convenience)
    
    Returns:
      32-byte key for AES-256-GCM
    """
    explicit = os.environ.get("VAULT_MASTER_KEY")
    if explicit:
        try:
            # Try hex first
            if explicit.startswith("0x") or all(c in "0123456789abcdefABCDEF" for c in explicit):
                return bytes.fromhex(explicit)
            # Try base64
            return base64.b64decode(explicit)
        except Exception as e:
            logger.warning(f"Failed to decode VAULT_MASTER_KEY, falling back to DB password: {e}")
    
    # Dev fallback: derive from DB password
    db_pass = os.environ.get("POSTGRES_PASSWORD", "mineralpass123")
    import hashlib
    return hashlib.sha256(f"mineral_vault:{db_pass}".encode()).digest()


def encrypt(plaintext: str) -> str:
    """
    Encrypt a plaintext API key using AES-256-GCM.
    
    Returns a base64-encoded string containing: nonce || ciphertext || tag
    This can be stored directly in a TEXT column.
    
    If cryptography is not available, falls back to base64 encoding (INSECURE).
    """
    if not plaintext:
        return ""
    
    if not CRYPTO_AVAILABLE:
        logger.warning("Vault encryption unavailable - using base64 (INSECURE)")
        return base64.b64encode(plaintext.encode()).decode()
    
    try:
        key = _derive_master_key()
        aesgcm = AESGCM(key)
        nonce = os.urandom(NONCE_SIZE)
        ciphertext_with_tag = aesgcm.encrypt(nonce, plaintext.encode(), None)
        # nonce || ciphertext_with_tag (tag is appended by GCM)
        combined = nonce + ciphertext_with_tag
        return base64.b64encode(combined).decode()
    except Exception as e:
        logger.error(f"Vault encryption failed: {e}")
        raise


def decrypt(ciphertext_b64: str) -> Optional[str]:
    """
    Decrypt a base64-encoded ciphertext from the vault.
    
    Returns None if decryption fails or if the vault is unavailable.
    """
    if not ciphertext_b64:
        return None
    
    if not CRYPTO_AVAILABLE:
        try:
            return base64.b64decode(ciphertext_b64).decode()
        except Exception as e:
            logger.warning(f"Vault decryption (base64 fallback) failed: {e}")
            return None
    
    try:
        key = _derive_master_key()
        aesgcm = AESGCM(key)
        combined = base64.b64decode(ciphertext_b64)
        
        if len(combined) < NONCE_SIZE + 16:  # nonce + minimum tag
            logger.warning("Vault ciphertext too short")
            return None
        
        nonce = combined[:NONCE_SIZE]
        ciphertext_with_tag = combined[NONCE_SIZE:]
        
        plaintext = aesgcm.decrypt(nonce, ciphertext_with_tag, None)
        return plaintext.decode()
    except Exception as e:
        logger.warning(f"Vault decryption failed: {e}")
        return None


def rotate(old_ciphertext_b64: str, new_plaintext: str) -> str:
    """
    Rotate a vault entry: decrypt old, encrypt new.
    Useful when the master key changes.
    
    If old decryption fails, just encrypt the new value (assume fresh entry).
    """
    # Attempt to decrypt old, but don't fail if we can't
    _ = decrypt(old_ciphertext_b64)
    return encrypt(new_plaintext)


__all__ = ["encrypt", "decrypt", "rotate", "CRYPTO_AVAILABLE"]
