"""AI provider health, configuration, and diagnostics router."""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.config import settings
from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import ApiResponse, ProviderDiagnosticsResponse
from database.models import User
from services.llm_client import (
    configured_providers,
    get_gemini_diagnostics,
    llm_available,
)
from models.ai_provider import GeminiProvider, OpenAIProvider, get_ai_provider

router = APIRouter(prefix="/api/v1/providers", tags=["AI Providers"])


@router.get("/diagnostics", response_model=ApiResponse[Dict[str, Any]])
def get_provider_diagnostics(user: Optional[User] = Depends(get_optional_current_user)):
    """Returns safe diagnostics for active AI models and connections (Requirement 9 & Amendments 1-2).

    Never displays or leaks raw API keys.
    """
    settings.reload()
    diag = get_gemini_diagnostics()

    # OpenAI optional status (Amendment 2)
    openai_key_configured = bool(settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip())
    openai_connection = "NOT CONFIGURED"
    if openai_key_configured:
        try:
            op = OpenAIProvider()
            ok, _ = op.test_connection()
            openai_connection = "SUCCESS" if ok else "FAILED"
        except Exception:
            openai_connection = "FAILED"

    result = {
        "gemini_configured": diag.get("gemini_configured", "NO") == "YES",
        "gemini_connection": diag.get("gemini_connection", "FAILED"),
        "active_provider": diag.get("active_provider", "Offline"),
        "active_model": diag.get("active_model", settings.GEMINI_MODEL),
        "detail": diag.get("detail", ""),
        "fallback_models": settings.GEMINI_FALLBACK_MODELS,
        "openai_configured": openai_key_configured,
        "openai_connection": openai_connection,
        "openai_model": settings.OPENAI_MODEL,
        "preferred_provider": settings.PREFERRED_PROVIDER,
    }
    return ApiResponse(success=True, data=result)


@router.post("/test", response_model=ApiResponse[Dict[str, Any]])
def test_provider_connection(user: Optional[User] = Depends(get_optional_current_user)):
    """Runs a minimal connectivity test on the active provider."""
    settings.reload()
    provider = get_ai_provider()
    success, detail = provider.test_connection()
    return ApiResponse(
        success=success,
        data={
            "provider_name": provider.get_model_name(),
            "connected": success,
            "detail": detail
        },
        message="Connection verified." if success else "Connection test failed."
    )


@router.get("", response_model=ApiResponse[Dict[str, Any]])
def get_active_provider_info(user: Optional[User] = Depends(get_optional_current_user)):
    """Lists configured providers and active models."""
    provs = configured_providers()
    return ApiResponse(success=True, data=provs)


@router.get("/telemetry", response_model=ApiResponse[Dict[str, Any]])
def get_provider_telemetry(user: Optional[User] = Depends(get_optional_current_user)):
    """Returns real-time provider circuit breaker states and latency metrics."""
    from models.ai_provider import AIProviderManager
    mgr = AIProviderManager()
    data = mgr.get_telemetry()
    return ApiResponse(success=True, data=data)
