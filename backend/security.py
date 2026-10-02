"""Security helpers: secret masking, safe errors, input checks."""
from __future__ import annotations

import re
from typing import Optional

from backend.config import settings

_SECRET_VALUES = lambda: [
    v for v in (settings.GEMINI_API_KEY, settings.OPENAI_API_KEY) if v and v.strip()
]


def mask_secret(value: Optional[str]) -> str:
    """Never display an API key. Returns status text only."""
    if not value or not str(value).strip():
        return "Not configured"
    return "Configured"


def redact_secrets(text: str) -> str:
    if not text:
        return text
    redacted = text
    for secret in _SECRET_VALUES():
        if secret and secret in redacted:
            redacted = redacted.replace(secret, "***")
    return redacted


def safe_user_error(exc: Exception) -> str:
    """User-facing error without stack traces or secrets."""
    message = redact_secrets(str(exc) or "An unexpected error occurred.")
    message = re.sub(r"(sk-|AIza)[A-Za-z0-9_\-]{8,}", "***", message)
    if len(message) > 280:
        message = message[:277] + "..."
    return message


def validate_positive_int(value, field: str, minimum: int = 1, maximum: int = 100) -> int:
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field} must be a whole number.")
    if number < minimum or number > maximum:
        raise ValueError(f"{field} must be between {minimum} and {maximum}.")
    return number


def validate_difficulty(value: str) -> str:
    allowed = {"easy", "medium", "hard"}
    cleaned = (value or "medium").strip().lower()
    if cleaned not in allowed:
        raise ValueError("Difficulty must be easy, medium, or hard.")
    return cleaned


# ============================================================================
# Password Hashing & Verification (PBKDF2-HMAC-SHA256)
# ============================================================================

import os
import hmac
import hashlib
from datetime import datetime, timedelta, timezone
import jwt

def hash_password(password: str) -> str:
    """Securely hash a password using PBKDF2-HMAC-SHA256 with random salt."""
    if not password:
        raise ValueError("Password cannot be empty.")
    salt = os.urandom(16)
    pw_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
    return f"{salt.hex()}${pw_hash.hex()}"


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against the stored salt$hash."""
    if not plain_password or not hashed_password or "$" not in hashed_password:
        return False
    try:
        salt_hex, hash_hex = hashed_password.split("$", 1)
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
        actual_hash = hashlib.pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 100_000)
        return hmac.compare_digest(actual_hash, expected_hash)
    except Exception:
        return False


# ============================================================================
# JWT Token Generation & Verification
# ============================================================================

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT access token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire, "iat": now, "type": "access"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Generates a signed JWT refresh token."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": now, "type": "refresh"})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> dict:
    """Decodes and validates a JWT token."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
