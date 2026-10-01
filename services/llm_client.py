"""Shared LLM client: Gemini primary, OpenAI fallback, offline-safe."""
from __future__ import annotations

from typing import Optional, Tuple, Dict, Any

from backend.config import settings
from backend.logging_config import logger
from models.ai_provider import (
    get_ai_provider,
    GeminiProvider,
    OpenAIProvider,
    OfflineMockProvider,
    AIProviderManager
)


def llm_available() -> bool:
    settings.reload()
    provider = get_ai_provider()
    return not isinstance(provider, OfflineMockProvider) and provider.is_available()


def configured_providers() -> dict:
    settings.reload()
    gemini = GeminiProvider()
    openai_p = OpenAIProvider()
    active_prov = get_ai_provider()
    return {
        "gemini": gemini.is_available(),
        "openai": openai_p.is_available(),
        "offline": True,
        "gemini_model": settings.GEMINI_MODEL,
        "openai_model": settings.OPENAI_MODEL,
        "embedding_model": settings.EMBEDDING_MODEL,
        "preferred": settings.PREFERRED_PROVIDER,
        "active": active_prov.get_model_name(),
    }


def get_gemini_diagnostics() -> Dict[str, str]:
    """
    Returns diagnostic status formatted for Requirement 9:
      Gemini configured: YES/NO
      Gemini connection: SUCCESS/FAILED
      Active provider: Gemini/Offline
      Active model: <model name>

    NEVER displays the API key value.
    """
    settings.reload()
    gemini = GeminiProvider()
    configured = "YES" if gemini.is_available() else "NO"

    if configured == "YES":
        success, detail = gemini.test_connection()
        connection = "SUCCESS" if success else "FAILED"
        active_prov = "Gemini" if success else "Offline"
        active_model = gemini.model if success else "Offline Academic Fallback"
    else:
        connection = "FAILED"
        active_prov = "Offline"
        active_model = "Offline Academic Fallback"
        detail = "Add GEMINI_API_KEY or GOOGLE_API_KEY to your .env file."

    return {
        "gemini_configured": configured,
        "gemini_connection": connection,
        "active_provider": active_prov,
        "active_model": active_model,
        "detail": detail,
    }


def call_llm(
    prompt: str,
    system_instruction: str = "",
    preferred: Optional[str] = None,
    allow_offline: bool = True
) -> Tuple[str, str]:
    """
    Returns (text, model_label) using AIProviderManager with automatic fallback resilience.
    """
    settings.reload()
    order = (preferred or settings.PREFERRED_PROVIDER or "auto").strip().lower()

    if order == "offline":
        mock = OfflineMockProvider()
        return mock.generate_text(prompt, system_instruction=system_instruction), mock.get_model_name()

    manager = AIProviderManager()
    text, provider_name, model_name, is_fb = manager.generate_text_with_resilience(
        prompt=prompt,
        system_instruction=system_instruction
    )

    if not allow_offline and provider_name == "Offline":
        raise RuntimeError("No LLM API key configured and offline fallback disabled.")

    return text, model_name
