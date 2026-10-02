"""Phase 2 Test Suite: AI Provider Manager & Fallback Resiliency.
Verifies Amendments 1-3:
- Gemini model-level fallback
- Optional OpenAI provider handling
- Circuit breaker state machine & health tracking
- AIProviderManager fallback resolution
"""
import time
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings, reload_env
from models.ai_provider import (
    GeminiProvider,
    OpenAIProvider,
    OfflineMockProvider,
    CircuitBreaker,
    AIProviderManager,
    get_ai_provider
)


@pytest.fixture
def client():
    return TestClient(app)


# ============================================================================
# 1. Circuit Breaker State Machine Tests
# ============================================================================

def test_circuit_breaker_transitions():
    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.1)
    assert cb.state == "CLOSED"
    assert cb.can_attempt() is True

    # First two failures - stays CLOSED
    cb.record_failure()
    assert cb.state == "CLOSED"
    cb.record_failure()
    assert cb.state == "CLOSED"

    # Third failure trips to OPEN
    cb.record_failure()
    assert cb.state == "OPEN"
    assert cb.can_attempt() is False

    # Wait for cooldown to expire
    time.sleep(0.15)
    # Transition to HALF_OPEN on next check
    assert cb.can_attempt() is True
    assert cb.state == "HALF_OPEN"

    # Success in HALF_OPEN resets to CLOSED
    cb.record_success(duration_ms=45.0)
    assert cb.state == "CLOSED"
    assert cb.consecutive_failures == 0

    stats = cb.get_stats()
    assert stats["state"] == "CLOSED"
    assert stats["avg_latency_ms"] == 45.0


# ============================================================================
# 2. Gemini Model-Level Fallback (Amendment 1)
# ============================================================================

def test_gemini_model_level_fallback(monkeypatch):
    """When the primary model encounters transient 503, fallback to alternate model."""
    provider = GeminiProvider(api_key="mock_test_key_123")
    monkeypatch.setattr(provider, "fallback_models", ["gemini-2.0-flash-lite", "gemini-1.5-flash"])

    call_models = []

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client

        def mock_generate(model, contents, config):
            call_models.append(model)
            if model == provider.model:
                raise Exception("503 Service Unavailable: High load on primary model")
            # Alternate model succeeds
            resp = MagicMock()
            resp.text = f"Success from alternate model: {model}"
            return resp

        mock_client.models.generate_content.side_effect = mock_generate

        # Patch time.sleep to run instantly in tests
        with patch("time.sleep", return_value=None):
            result = provider.generate_text("Explain binary search")

        assert "Success from alternate model" in result
        assert provider.model in call_models
        assert "gemini-2.0-flash-lite" in call_models


def test_gemini_auth_error_fails_fast():
    """Invalid credentials should fail immediately without silent model fallback."""
    provider = GeminiProvider(api_key="invalid_bad_key")

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.generate_content.side_effect = Exception("401 API_KEY_INVALID: User not authenticated")

        with pytest.raises(RuntimeError) as exc_info:
            provider.generate_text("Hello")

        assert "API error" in str(exc_info.value)


# ============================================================================
# 3. Optional OpenAI Provider (Amendment 2)
# ============================================================================

def test_openai_optional_handling(monkeypatch):
    # Without key
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    op = OpenAIProvider(api_key="")
    assert op.is_available() is False
    ok, msg = op.test_connection()
    assert ok is False
    assert "NOT CONFIGURED" in msg

    # With key configured
    op_with_key = OpenAIProvider(api_key="sk-test-key-mock")
    assert op_with_key.is_available() is True


# ============================================================================
# 4. AIProviderManager End-to-End Fallback Chain
# ============================================================================

def test_provider_manager_fallback_to_offline(monkeypatch):
    """When all remote providers are unavailable or fail, cleanly fall back to Offline."""
    manager = AIProviderManager()

    # Simulate both Gemini and OpenAI failing
    with patch.object(GeminiProvider, "is_available", return_value=False):
        with patch.object(OpenAIProvider, "is_available", return_value=False):
            text, prov, model, is_fallback = manager.generate_text_with_resilience("Create a study timetable")

            assert is_fallback is True
            assert prov == "Offline"
            assert "Study Plan" in text


def test_provider_manager_telemetry_endpoint(client):
    """Verify /api/v1/providers/telemetry reports circuit breaker states without secret leakage."""
    resp = client.get("/api/v1/providers/telemetry")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "gemini" in data
    assert "openai" in data
    assert "circuit" in data["gemini"]
    assert "circuit" in data["openai"]
    assert "active_provider" in data

    # Verify no API keys exposed
    text = resp.text
    assert "AIza" not in text
    assert "sk-" not in text
