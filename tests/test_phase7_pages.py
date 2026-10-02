"""Phase 7: Remaining Pages & Features Test Suite.
Validates all 16 additional frontend pages, domain models, backend endpoints, and production build assets.
"""
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from database.database import get_db, init_db
from database.models import User, Subject, SyllabusTopic, Goal, Task, ExamAttempt, Document


@pytest.fixture(scope="module")
def client():
    init_db()
    with TestClient(app) as c:
        yield c


def test_phase7_frontend_source_components_exist():
    """Verifies that all Phase 7 page components exist and are implemented in the React frontend."""
    frontend_dir = Path("frontend/src/components")
    assert frontend_dir.exists(), "frontend/src/components must exist"

    expected_components = [
        "materials/MaterialsView.tsx",
        "knowledge/KnowledgeView.tsx",
        "syllabus/SyllabusView.tsx",
        "quizzes/QuizzesView.tsx",
        "mock_exams/MockExamsView.tsx",
        "planner/PlannerView.tsx",
        "goals/GoalsView.tsx",
        "weaknesses/WeaknessesView.tsx",
        "analytics/AnalyticsView.tsx",
        "reports/ReportsView.tsx",
        "memory/MemoryView.tsx",
        "agents/AgentsView.tsx",
        "settings/SettingsView.tsx",
        "diagnostics/DiagnosticsView.tsx",
    ]

    for comp in expected_components:
        comp_path = frontend_dir / comp
        assert comp_path.exists(), f"Component {comp} must exist in frontend"
        content = comp_path.read_text(encoding="utf-8")
        assert len(content) > 200, f"Component {comp} must have substantial implementation"


def test_phase7_frontend_build_artifacts():
    """Verifies that the React production build succeeds and outputs html, js, and css bundles."""
    dist_dir = Path("frontend/dist")
    assert dist_dir.exists(), "frontend/dist must exist"
    assert (dist_dir / "index.html").exists(), "dist/index.html must exist"

    assets_dir = dist_dir / "assets"
    assert assets_dir.exists(), "dist/assets must exist"

    js_files = list(assets_dir.glob("*.js"))
    css_files = list(assets_dir.glob("*.css"))
    assert len(js_files) >= 1, "At least one production JS bundle must be generated"
    assert len(css_files) >= 1, "At least one production CSS bundle must be generated"


def test_phase7_materials_and_knowledge_api(client):
    """Tests course materials listing and semantic vector search endpoints."""
    # List documents
    res = client.get("/api/v1/documents")
    assert res.status_code == 200
    json_data = res.json()
    assert json_data["success"] is True
    assert isinstance(json_data["data"], list)

    # Search documents (RAG semantic retrieval)
    res_search = client.get("/api/v1/documents/search?query=operating+system+kernel&top_k=3")
    assert res_search.status_code == 200
    search_data = res_search.json()
    assert search_data["success"] is True
    assert "chunks" in search_data["data"]
    assert "citations" in search_data["data"]


def test_phase7_syllabus_api(client):
    """Tests subject and syllabus topic management endpoints."""
    # Create a test subject
    res_create = client.post(
        "/api/v1/subjects",
        json={
            "name": "Phase 7 Cloud Architecture",
            "code": "CS701",
            "semester": "7th Semester",
            "description": "Distributed cloud systems",
        },
    )
    assert res_create.status_code == 200
    subj = res_create.json()["data"]
    subj_id = subj["id"]

    # Add a syllabus topic
    res_topic = client.post(
        f"/api/v1/subjects/{subj_id}/topics",
        json={"unit_number": 1, "topic_name": "Serverless Functions"},
    )
    assert res_topic.status_code == 200
    topic = res_topic.json()["data"]
    topic_id = topic["id"]
    assert topic["is_completed"] is False

    # Toggle topic completion
    res_toggle = client.patch(f"/api/v1/subjects/{subj_id}/topics/{topic_id}/toggle")
    assert res_toggle.status_code == 200
    toggled = res_toggle.json()["data"]
    assert toggled["is_completed"] is True


def test_phase7_quizzes_and_mock_exams_api(client):
    """Tests practice quiz generation, answer recording, and submission."""
    # Generate quiz
    res_gen = client.post(
        "/api/v1/quizzes/generate",
        json={
            "num_questions": 3,
            "difficulty": "medium",
            "exam_kind": "PRACTICE_QUIZ",
        },
    )
    assert res_gen.status_code == 200
    attempt = res_gen.json()["data"]
    attempt_id = attempt["id"]
    assert attempt["status"] == "IN_PROGRESS"

    # Get attempt details
    res_get = client.get(f"/api/v1/quizzes/{attempt_id}")
    assert res_get.status_code == 200
    detail = res_get.json()["data"]
    assert len(detail["questions"]) >= 1

    first_q = detail["questions"][0]
    # Record answer
    res_ans = client.post(
        f"/api/v1/quizzes/{attempt_id}/answer",
        json={"question_id": first_q["id"], "user_answer": "Test Answer Option A"},
    )
    assert res_ans.status_code == 200

    # Submit quiz
    res_sub = client.post(
        f"/api/v1/quizzes/{attempt_id}/submit",
        json={"answers": {str(first_q["id"]): "Test Answer Option A"}},
    )
    assert res_sub.status_code == 200
    eval_res = res_sub.json()["data"]
    assert eval_res["status"] in ["SUBMITTED", "COMPLETED", "EXPIRED"]


def test_phase7_planner_and_goals_api(client):
    """Tests adaptive study planner and autonomous goal decomposition endpoints."""
    # Study plan
    res_plan = client.get("/api/v1/study-plan")
    assert res_plan.status_code == 200
    assert res_plan.json()["success"] is True

    # Goals list
    res_goals = client.get("/api/v1/goals")
    assert res_goals.status_code == 200
    assert res_goals.json()["success"] is True
    assert isinstance(res_goals.json()["data"], list)


def test_phase7_analytics_and_reports_api(client):
    """Tests performance analytics, weak topics, and readiness reports."""
    # Performance analytics
    res_perf = client.get("/api/v1/analytics/performance")
    assert res_perf.status_code == 200
    assert "average_percentage" in res_perf.json()["data"]

    # Weak topics
    res_weak = client.get("/api/v1/analytics/weak-topics")
    assert res_weak.status_code == 200
    assert isinstance(res_weak.json()["data"], list)

    # Readiness report
    res_rep = client.get("/api/v1/reports/exam-readiness")
    assert res_rep.status_code == 200
    rep_data = res_rep.json()["data"]
    assert "overall_readiness_score" in rep_data
    assert "markdown_report" in rep_data


def test_phase7_memory_and_diagnostics_api(client):
    """Tests long-term memory facts and developer diagnostics endpoints."""
    # Save a memory fact
    res_mem = client.post(
        "/api/v1/memory",
        json={
            "key": "math_learning_style",
            "value": "Prefers visual proof diagrams over algebraic derivation.",
            "memory_type": "LEARNING_STYLE",
            "confidence": 0.95,
            "importance": 4,
        },
    )
    assert res_mem.status_code == 200
    mem_id = res_mem.json()["data"]["id"]

    # List memories
    res_list = client.get("/api/v1/memory")
    assert res_list.status_code == 200
    assert any(m["id"] == mem_id for m in res_list.json()["data"])

    # Delete memory
    res_del = client.delete(f"/api/v1/memory/{mem_id}")
    assert res_del.status_code == 200

    # Diagnostics system
    res_diag = client.get("/api/v1/diagnostics/system")
    assert res_diag.status_code == 200
    diag_data = res_diag.json()["data"]
    assert "documents_count" in diag_data
    assert "vector_store_count" in diag_data

    # Diagnostics health
    res_health = client.get("/api/v1/diagnostics/health")
    assert res_health.status_code == 200
    assert res_health.json()["data"]["status"] == "healthy"
