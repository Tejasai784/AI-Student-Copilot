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
