"""Tests for Phase 1 Foundation:
- Student Profile & Preferences
- Multi-format Document Ingestion (PDF, DOCX, TXT, CSV)
- Vector Indexing & Semantic Search
- Goal Understanding & Subtask Decomposition
- Student Memory & Privacy Filtering
- FastAPI REST Endpoints
"""
import io
import pytest
from pathlib import Path
from fastapi.testclient import TestClient

from database.crud import (
    create_or_update_student_profile,
    get_student_profile,
    create_subject,
    get_subjects
)
from services.goal_service import parse_goal_intent, create_goal_and_tasks_from_prompt
from memory.memory_manager import MemoryManager
from rag.document_loader import extract_text_from_txt, extract_text_from_csv, extract_text_from_file
from backend.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_student_profile_lifecycle(db_session):
    p = create_or_update_student_profile(
        db=db_session,
        name="Ananya Verma",
        course="B.Tech Computer Science",
        branch="Artificial Intelligence",
        year="3rd Year",
        semester="6th Semester"
    )
    assert p.id is not None
    assert p.name == "Ananya Verma"

    fetched = get_student_profile(db_session)
    assert fetched is not None
    assert fetched.name == "Ananya Verma"


def test_txt_and_csv_document_extraction():
    # Test TXT extraction
    sample_text = "Unit 1: Python Basics. Variables and Dynamic Typing.\nUnit 2: Lists, Dictionaries, Sets."
    txt_pages = extract_text_from_txt(sample_text.encode("utf-8"))
    assert len(txt_pages) >= 1
    assert "Python Basics" in txt_pages[0]["text"]

    # Test CSV extraction
    sample_csv = "topic,unit,weight\nVariables,1,10\nLoops,2,15\nFunctions,3,20\n"
    csv_pages = extract_text_from_csv(sample_csv.encode("utf-8"))
    assert len(csv_pages) >= 1
    assert "CSV Summary" in csv_pages[0]["text"]
    assert "Variables" in csv_pages[0]["text"]


def test_goal_understanding_and_decomposition(db_session):
    subj = create_subject(db_session, "Python Programming", "CS204", "4th Semester")
    prompt = "Prepare me for my Python exam in 7 days."
    
    parsed = parse_goal_intent(prompt)
    assert parsed["days"] == 7
    assert "Python" in parsed["subject_hint"]
    assert len(parsed["constraints"]) > 0

    goal, tasks = create_goal_and_tasks_from_prompt(db_session, prompt, subject_id=subj.id)
    assert goal.id is not None
    assert len(tasks) >= 4
    assert any("Syllabus" in t.title for t in tasks)
    assert any("Practice" in t.title or "Exam" in t.title for t in tasks)


def test_memory_manager_privacy_and_context(db_session):
    mgr = MemoryManager(db_session)
    
    # Store standard preference
    m1 = mgr.store_fact(key="study_style", value="Prefers step-by-step code walkthroughs", memory_type="preference", importance=2)
    assert m1 is not None

    # Sensitive data filter should block credentials
    m_sensitive = mgr.store_fact(key="secret_token", value="sk-proj-1234567890abcdef", memory_type="preference")
    assert m_sensitive is None

    # Context retrieval
    ctx = mgr.get_context_for_prompt("How should I study code?")
    assert "step-by-step code walkthroughs" in ctx


def test_fastapi_rest_endpoints(client):
    # Health endpoint
    res_health = client.get("/api/health")
    assert res_health.status_code == 200
    data_health = res_health.json()
    assert data_health["status"] == "healthy"
    assert "ai_providers" in data_health

    # Dashboard summary endpoint
    res_dash = client.get("/api/dashboard/summary")
    assert res_dash.status_code == 200

    # Profile endpoint
    res_prof = client.post("/api/profile", json={
        "name": "Rohan Gupta",
        "course": "B.Tech Computer Science",
        "branch": "Data Science",
        "year": "2nd Year",
        "semester": "4th Semester"
    })
    assert res_prof.status_code == 200
    assert res_prof.json()["name"] == "Rohan Gupta"

    # Chat endpoint
    res_chat = client.post("/api/chat", json={
        "query": "What are the core units in Python?"
    })
    assert res_chat.status_code == 200
    chat_data = res_chat.json()
    assert chat_data["ok"] is True
    assert len(chat_data["reply"]) > 20
