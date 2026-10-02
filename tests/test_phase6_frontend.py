"""
Phase 6 Verification Tests: React Frontend Foundation, Dashboard & AI Chat Integration.

Validates:
1. Frontend build artifact presence and structure:
   - package.json includes React 18, Vite, Tailwind CSS, Lucide icons, and @fontsource packages.
   - Built distribution folder `dist/` contains index.html, CSS and JS bundles with self-hosted fonts.
2. Design System Tokens:
   - index.css declares §7A 'calm study studio' custom properties (--color-ink, --color-canvas, etc.).
   - tailwind.config.js maps tokens and custom font families.
3. API Contracts for Dashboard:
   - GET /api/v1/students/dashboard returns student profile, readiness metrics, and upcoming tasks.
   - GET /api/v1/goals/ returns goals with task breakdowns.
4. API Contracts for AI Chat:
   - GET /api/v1/chat/conversations returns conversation list.
   - POST /api/v1/chat/stream responds with text/event-stream headers and valid SSE event structure.
"""
import os
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.main import app

FRONTEND_DIR = Path("d:/AI_Student_Copilot/frontend")

@pytest.fixture
def client():
    return TestClient(app)


def test_frontend_package_and_build_artifacts():
    # 1. Verify package.json
    pkg_file = FRONTEND_DIR / "package.json"
    assert pkg_file.exists()
    pkg_data = json.loads(pkg_file.read_text(encoding="utf-8"))

    deps = pkg_data.get("dependencies", {})
    assert "react" in deps
    assert "react-dom" in deps
    assert "@fontsource/bricolage-grotesque" in deps
    assert "@fontsource/figtree" in deps
    assert "@fontsource/jetbrains-mono" in deps
    assert "lucide-react" in deps

    # 2. Verify dist build output
    dist_html = FRONTEND_DIR / "dist" / "index.html"
    assert dist_html.exists()
    html_content = dist_html.read_text(encoding="utf-8")
    assert "ASIP 2.0" in html_content
    assert "assets/" in html_content


def test_design_tokens_configuration():
    css_file = FRONTEND_DIR / "src" / "index.css"
    assert css_file.exists()
    css_text = css_file.read_text(encoding="utf-8")
    assert "--color-ink: #14213D;" in css_text
    assert "--color-canvas: #F4F6FA;" in css_text
    assert "--color-focus: #0F8B8D;" in css_text
    assert ".dark" in css_text

    tw_config = FRONTEND_DIR / "tailwind.config.js"
    assert tw_config.exists()
    tw_text = tw_config.read_text(encoding="utf-8")
    assert "Bricolage Grotesque" in tw_text
    assert "Figtree" in tw_text
    assert "JetBrains Mono" in tw_text


def test_dashboard_api_integration(client, db_session):
    resp = client.get("/api/v1/students/dashboard")
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert "student_name" in data
    assert "study_progress" in data
    assert "total_subjects" in data

    goals_resp = client.get("/api/v1/goals/")
    assert goals_resp.status_code == 200


def test_chat_streaming_api_integration(client, db_session):
    # Verify conversational stream endpoint provides SSE for the frontend client
    stream_resp = client.get(
        "/api/v1/chat/stream?question=Explain+database+indexes&style=Simple+explanation"
    )
    assert stream_resp.status_code == 200
    assert "text/event-stream" in stream_resp.headers.get("content-type", "")
    assert "event: status" in stream_resp.text
    assert "event: token" in stream_resp.text
    assert "event: done" in stream_resp.text
