"""Phase 1 V2 API Test Suite.
Verifies all new V1 REST endpoints, JWT authentication, SSE streaming headers,
error handling, and zero regression across the backend.
"""
import io
import pytest
from fastapi.testclient import TestClient
from backend.main import app
from database.models import User

@pytest.fixture
def client():
    return TestClient(app)


# ============================================================================
# 1. Authentication & Security
# ============================================================================

def test_auth_workflow(client):
    # Register new user
    import time
    username = f"test_user_{int(time.time() * 1000)}"
    reg_res = client.post("/api/v1/auth/register", json={
        "username": username,
        "email": f"{username}@example.com",
        "password": "SecurePassword123!",
        "full_name": "Test Student"
    })
    assert reg_res.status_code == 200
    assert reg_res.json()["success"] is True
    assert reg_res.json()["data"]["username"] == username

    # Login with wrong password
    bad_login = client.post("/api/v1/auth/login", json={
        "username": username,
        "password": "WrongPassword!"
    })
    assert bad_login.status_code == 401

    # Login with correct password
    login_res = client.post("/api/v1/auth/login", json={
        "username": username,
        "password": "SecurePassword123!"
    })
    assert login_res.status_code == 200
    login_data = login_res.json()["data"]
    assert "access_token" in login_data
    token = login_data["access_token"]

    # Access protected route /me with Bearer token
    me_res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["data"]["username"] == username

    # Logout
    logout_res = client.post("/api/v1/auth/logout")
    assert logout_res.status_code == 200


# ============================================================================
# 2. Students & Profile
# ============================================================================

def test_students_api(client):
    # Get profile
    prof_res = client.get("/api/v1/students/profile")
    assert prof_res.status_code == 200
    assert prof_res.json()["success"] is True

    # Update profile
    upd_res = client.put("/api/v1/students/profile", json={
        "name": "Jordan Lee",
        "course": "B.Tech Computer Science",
        "branch": "AI & ML",
        "year": "4th Year",
        "semester": "7th Semester"
    })
    assert upd_res.status_code == 200
    assert upd_res.json()["data"]["name"] == "Jordan Lee"

    # Settings
    set_res = client.get("/api/v1/students/settings")
    assert set_res.status_code == 200
    assert "preferred_provider" in set_res.json()["data"]

    # Dashboard
    dash_res = client.get("/api/v1/students/dashboard")
    assert dash_res.status_code == 200
    assert dash_res.json()["success"] is True


# ============================================================================
# 3. Subjects & Topics
# ============================================================================

def test_subjects_api(client):
    # Create subject
    import time
    code = f"CS_{int(time.time() % 10000)}"
    sub_res = client.post("/api/v1/subjects", json={
        "name": "Software Engineering",
        "code": code,
        "semester": "6th Semester",
        "description": "Agile methodologies, testing, CI/CD"
    })
    assert sub_res.status_code == 200
    sub_id = sub_res.json()["data"]["id"]

    # Add topic
    top_res = client.post(f"/api/v1/subjects/{sub_id}/topics", json={
        "unit_number": 1,
        "topic_name": "Agile Scrum Methodology"
    })
    assert top_res.status_code == 200
    top_id = top_res.json()["data"]["id"]

    # Toggle topic
    tog_res = client.patch(f"/api/v1/subjects/{sub_id}/topics/{top_id}/toggle")
    assert tog_res.status_code == 200
    assert tog_res.json()["data"]["is_completed"] is True

    # Get subject details
    det_res = client.get(f"/api/v1/subjects/{sub_id}")
    assert det_res.status_code == 200
    assert det_res.json()["data"]["topics_count"] >= 1


# ============================================================================
# 4. Documents & RAG API
# ============================================================================

def test_documents_api(client):
    # List documents
    docs_res = client.get("/api/v1/documents")
    assert docs_res.status_code == 200

    # Upload sample text document
    sample_text = b"Unit 1: Software Design Patterns. Singleton, Factory, and Observer patterns."
    upload_res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("design_patterns.txt", io.BytesIO(sample_text), "text/plain")},
        data={"subject_id": 1, "document_type": "Lecture Notes"}
    )
    assert upload_res.status_code == 200
    doc_id = upload_res.json()["data"]["id"]

    # Get document chunks
    chunks_res = client.get(f"/api/v1/documents/{doc_id}/chunks")
    assert chunks_res.status_code == 200
    assert len(chunks_res.json()["data"]) >= 1

    # Delete document
    del_res = client.delete(f"/api/v1/documents/{doc_id}")
    assert del_res.status_code == 200


# ============================================================================
# 5. AI Chat & SSE Stream
# ============================================================================

def test_chat_api(client):
    # Ask AI tutor
    ask_res = client.post("/api/v1/chat/ask", json={
        "question": "What is the difference between compiler and interpreter in computer science?",
        "style": "Simple explanation"
    })
    assert ask_res.status_code == 200
    data = ask_res.json()["data"]
    assert "answer" in data
    assert len(data["answer"]) > 10
    assert "model_used" in data

    # List conversations
    conv_res = client.get("/api/v1/chat/conversations")
    assert conv_res.status_code == 200
    assert len(conv_res.json()["data"]) >= 1

    # SSE streaming connection
    stream_res = client.get("/api/v1/chat/stream?question=Explain+recursion")
    assert stream_res.status_code == 200
    assert "text/event-stream" in stream_res.headers.get("content-type", "")


# ============================================================================
# 6. Study Plan & Quizzes
# ============================================================================

def test_study_plan_and_quizzes(client):
    # Generate study plan
    plan_res = client.post("/api/v1/study-plan/generate", json={
        "horizon": "weekly",
        "daily_minutes": 45
    })
    assert plan_res.status_code == 200
    plan_data = plan_res.json()["data"]
    assert plan_data["horizon"] == "weekly"
    assert len(plan_data["tasks"]) > 0

    # Toggle task
    first_task_id = plan_data["tasks"][0]["id"]
    tog_task = client.patch(f"/api/v1/study-plan/tasks/{first_task_id}/toggle")
    assert tog_task.status_code == 200

    # Generate practice quiz
    quiz_res = client.post("/api/v1/quizzes/generate", json={
        "num_questions": 3,
        "difficulty": "medium",
        "exam_kind": "practice"
    })
    assert quiz_res.status_code == 200
    attempt_id = quiz_res.json()["data"]["id"]

    # View quiz
    view_res = client.get(f"/api/v1/quizzes/{attempt_id}")
    assert view_res.status_code == 200
    questions = view_res.json()["data"]["questions"]
    assert len(questions) >= 1

    # Answer and submit
    first_q = questions[0]
    client.post(f"/api/v1/quizzes/{attempt_id}/answer", json={
        "question_id": first_q["id"],
        "user_answer": "Sample answer for testing"
    })
    sub_res = client.post(f"/api/v1/quizzes/{attempt_id}/submit")
    assert sub_res.status_code == 200
    assert sub_res.json()["data"]["status"] == "SUBMITTED"


# ============================================================================
# 7. Diagnostics & Providers
# ============================================================================

def test_diagnostics_and_providers(client):
    # Health probe
    h_res = client.get("/api/v1/diagnostics/health")
    assert h_res.status_code == 200
    assert h_res.json()["data"]["status"] == "healthy"

    # System metrics
    sys_res = client.get("/api/v1/diagnostics/system")
    assert sys_res.status_code == 200
    assert "upload_storage_mb" in sys_res.json()["data"]

    # Provider diagnostics (Requirement 9 & Amendments 1-2)
    p_res = client.get("/api/v1/providers/diagnostics")
    assert p_res.status_code == 200
    p_data = p_res.json()["data"]
    assert "gemini_configured" in p_data
    assert "gemini_connection" in p_data
    assert "active_provider" in p_data
    assert "active_model" in p_data
    assert "fallback_models" in p_data
    # Verify no raw API keys are exposed
    raw_text = p_res.text
    assert "AIza" not in raw_text
    assert "sk-" not in raw_text


def test_cors_configuration(client):
    """Verifies that CORS allows Vercel production origin and localhost while rejecting unauthorized origins."""
    # 1. Preflight OPTIONS for Vercel production origin
    res_vercel_options = client.options(
        "/api/v1/diagnostics/health",
        headers={
            "Origin": "https://ai-student-copilot-pi.vercel.app",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization,content-type",
        }
    )
    assert res_vercel_options.status_code == 200
    assert res_vercel_options.headers.get("access-control-allow-origin") == "https://ai-student-copilot-pi.vercel.app"
    assert res_vercel_options.headers.get("access-control-allow-credentials") == "true"

    # 2. Simple GET for Vercel production origin
    res_vercel_get = client.get(
        "/api/v1/diagnostics/health",
        headers={"Origin": "https://ai-student-copilot-pi.vercel.app"}
    )
    assert res_vercel_get.status_code == 200
    assert res_vercel_get.headers.get("access-control-allow-origin") == "https://ai-student-copilot-pi.vercel.app"

    # 3. Localhost origin
    res_local = client.get(
        "/api/v1/diagnostics/health",
        headers={"Origin": "http://localhost:5173"}
    )
    assert res_local.status_code == 200
    assert res_local.headers.get("access-control-allow-origin") == "http://localhost:5173"

    # 4. Vercel preview domain (regex)
    res_preview = client.get(
        "/api/v1/diagnostics/health",
        headers={"Origin": "https://ai-student-copilot-git-test.vercel.app"}
    )
    assert res_preview.status_code == 200
    assert res_preview.headers.get("access-control-allow-origin") == "https://ai-student-copilot-git-test.vercel.app"

    # 5. Unauthorized origin
    res_unauth = client.get(
        "/api/v1/diagnostics/health",
        headers={"Origin": "https://unauthorized-origin.com"}
    )
    assert res_unauth.headers.get("access-control-allow-origin") is None
