"""Tests for robust Gemini AI integration and diagnostics."""
import os
import pytest
from unittest.mock import patch, MagicMock
from backend.config import settings, reload_env
from models.ai_provider import GeminiProvider, get_ai_provider
from services.llm_client import llm_available, configured_providers, get_gemini_diagnostics
from services.tutor_service import get_tutor_response, TutorResponse
from fastapi.testclient import TestClient
from backend.main import app


def test_gemini_key_resolution_and_aliases(monkeypatch):
    """Test that GEMINI_API_KEY and GOOGLE_API_KEY are resolved dynamically."""
    # Ensure clean slate
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_API_KEY", raising=False)
    monkeypatch.delenv("AI_API_KEY", raising=False)

    reload_env()
    assert settings.GEMINI_API_KEY == ""

    # Test setting GOOGLE_API_KEY only
    monkeypatch.setenv("GOOGLE_API_KEY", "test_google_key_123")
    reload_env()
    assert settings.GEMINI_API_KEY == "test_google_key_123"
    assert settings.GOOGLE_API_KEY == "test_google_key_123"

    # Test GeminiProvider reflects this key
    provider = GeminiProvider()
    assert provider.is_available() is True
    assert provider.api_key == "test_google_key_123"


def test_gemini_model_configuration(monkeypatch):
    """Verify configured model name is gemini-2.0-flash and respects env override."""
    monkeypatch.delenv("GEMINI_MODEL", raising=False)
    monkeypatch.delenv("AI_MODEL", raising=False)
    assert settings.GEMINI_MODEL == "gemini-2.0-flash"

    provider = GeminiProvider()
    assert "gemini-2.0-flash" in provider.get_model_name()

    # With override
    monkeypatch.setenv("GEMINI_MODEL", "gemini-2.5-flash")
    assert settings.GEMINI_MODEL == "gemini-2.5-flash"
    assert "gemini-2.5-flash" in GeminiProvider().get_model_name()


def test_gemini_connectivity_test_safe_no_leak(monkeypatch):
    """Test that test_connection returns True on success and sanitized msg on failure."""
    provider = GeminiProvider(api_key="fake_secret_key_AIzaSyFakeKey12345678901234567")

    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.get.return_value = {"name": "gemini-2.0-flash"}

        success, msg = provider.test_connection()
        assert success is True
        assert msg == "SUCCESS"

    # Test failure sanitization
    with patch("google.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        mock_client.models.get.side_effect = Exception("403 Forbidden with key=AIzaSyFakeKey12345678901234567")

        success, msg = provider.test_connection()
        assert success is False
        assert "AIzaSyFakeKey12345678901234567" not in msg
        assert "[REDACTED]" in msg


def test_gemini_diagnostics_format():
    """Verify diagnostics formatting adheres to Requirement 9."""
    diag = get_gemini_diagnostics()
    assert "gemini_configured" in diag
    assert diag["gemini_configured"] in ["YES", "NO"]
    assert "gemini_connection" in diag
    assert "active_provider" in diag
    assert "active_model" in diag
    # Ensure no API key in any diagnostic values
    for val in diag.values():
        assert "AIza" not in str(val)
        assert "sk-" not in str(val)


def test_api_diagnostics_endpoint():
    """Test that /api/diagnostics endpoint outputs the 4 required fields and no secret."""
    client = TestClient(app)
    resp = client.get("/api/diagnostics")
    assert resp.status_code == 200
    data = resp.json()
    assert "gemini_configured" in data
    assert "gemini_connection" in data
    assert "active_provider" in data
    assert "active_model" in data
    assert "api_key" not in json_str(data)


def test_rag_tutor_pipeline_with_gemini(monkeypatch):
    """Test RAG pipeline flow: Question -> Retrieval -> Gemini -> Answer -> Sources."""
    monkeypatch.setenv("GEMINI_API_KEY", "mock_key")

    with patch("models.ai_provider.GeminiProvider.generate_text") as mock_gen:
        mock_gen.return_value = "This is a verified Gemini explanation of Python functions."

        resp = get_tutor_response(
            query="Explain functions in Python",
            subject_id=None,
            answer_mode="Simple explanation"
        )
        assert resp.answer != ""
        assert "This is a verified Gemini explanation" in resp.answer
        assert resp.source_mode in ["material", "no_material"]


def json_str(obj) -> str:
    import json
    return json.dumps(obj)
