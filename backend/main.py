"""AGI-Inspired Autonomous Student Intelligence Platform (ASIP) - FastAPI Backend.
Exposes full REST API with interactive OpenAPI documentation (/docs).
"""
from __future__ import annotations

import json
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from pathlib import Path
from fastapi import FastAPI, Depends, HTTPException, UploadFile, File, Form, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.config import settings
from backend.logging_config import logger
from backend.security import mask_secret, safe_user_error
from database.database import init_db, get_db
from database.crud import (
    get_student_profile,
    create_or_update_student_profile,
    get_subjects,
    get_subject_by_id,
    create_subject,
    add_topic,
    toggle_topic_completion,
    get_documents,
    get_document_by_id,
    delete_document_record,
    get_dashboard_summary,
    create_goal,
    get_goals,
    get_goal_by_id,
    create_task,
    toggle_task_completion,
    create_conversation,
    get_conversations,
    get_messages,
    add_message,
    save_memory,
    get_memories,
    delete_memory,
    get_agent_runs
)
from services.document_service import save_and_process_document, delete_document_with_files
from services.llm_client import call_llm, configured_providers, llm_available, get_gemini_diagnostics
from services.goal_service import create_goal_and_tasks_from_prompt
from services.autonomous_workflow import AutonomousLearningCoordinator
from services.analytics_service import compute_performance, detect_weak_topics, generate_knowledge_map
from services.report_service import generate_exam_readiness_report
from agents.orchestrator import route_request
from tools.registry import get_tool_registry
from rag.vector_store import get_vector_store
from rag.embeddings import get_embedding_generator


# Initialize Database Tables
try:
    init_db()
except Exception as e:
    logger.critical(f"Database init error: {e}", exc_info=True)


app = FastAPI(
    title="AGI-Inspired Autonomous Student Intelligence Platform (ASIP)",
    description="Full-stack AI platform combining planning, reasoning, memory, tool use, multiple specialist agents, self-evaluation, and autonomous task execution.",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS Middleware with strict origin allowlist
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================================
# MOUNT MODULAR V1 ROUTERS
# ============================================================================
from backend.routers import (
    auth,
    students,
    subjects,
    documents,
    chat,
    study_plan,
    quizzes,
    analytics,
    reports,
    memory,
    agents,
    providers,
    diagnostics,
    goals,
)

app.include_router(auth.router)
app.include_router(students.router)
app.include_router(subjects.router)
app.include_router(documents.router)
app.include_router(chat.router)
app.include_router(study_plan.router)
app.include_router(quizzes.router)
app.include_router(analytics.router)
app.include_router(reports.router)
app.include_router(memory.router)
app.include_router(agents.router)
app.include_router(providers.router)
app.include_router(diagnostics.router)
app.include_router(goals.router)


# Dependency to get DB session
def get_db_session():
    with get_db() as session:
        yield session


# ============================================================================
# PYDANTIC SCHEMAS
# ============================================================================

class ProfileUpdateRequest(BaseModel):
    name: str
    course: str
    branch: str = "Computer Science"
    year: str = "3rd Year"
    semester: str = "6th Semester"

class SubjectCreateRequest(BaseModel):
    name: str
    code: str
    semester: str = "6th Semester"
    description: Optional[str] = None

class TopicCreateRequest(BaseModel):
    unit_number: int = 1
    topic_name: str

class ChatRequest(BaseModel):
    query: str
    conversation_id: Optional[int] = None
    subject_id: Optional[int] = None

class GoalCreateRequest(BaseModel):
    title: str
    objective: str
    days: Optional[int] = 7
    subject_id: Optional[int] = None

class OrchestrateRequest(BaseModel):
    query: str
    subject_id: Optional[int] = None

class AutonomousPrepRequest(BaseModel):
    goal_prompt: str = "Prepare me for my Python exam in 7 days."
    subject_id: Optional[int] = None

class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]

class MemoryCreateRequest(BaseModel):
    key: str
    value: str
    memory_type: str = "preference"
    importance: int = 3


# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/api/health", tags=["System"])
def health_check(db: Session = Depends(get_db_session)):
    """System health check and diagnostic status."""
    v_store = get_vector_store()
    return {
        "status": "healthy",
        "app_name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.APP_ENV,
        "database": "connected",
        "vector_store_chunks": v_store.count(),
        "ai_providers": configured_providers(),
        "registered_tools_count": len(get_tool_registry().list_tools()),
        "timestamp": datetime.now(timezone.utc).isoformat()
    }


@app.get("/api/dashboard/summary", tags=["Dashboard"])
def get_dashboard(db: Session = Depends(get_db_session)):
    """Returns aggregated student metrics and study statistics."""
    return get_dashboard_summary(db)


@app.get("/api/profile", tags=["Profile"])
def get_profile(db: Session = Depends(get_db_session)):
    """Retrieves student profile."""
    p = get_student_profile(db)
    if not p:
        return {"profile_set": False}
    return {
        "profile_set": True,
        "name": p.name,
        "course": p.course,
        "branch": p.branch,
        "year": p.year,
        "semester": p.semester
    }


@app.post("/api/profile", tags=["Profile"])
def update_profile(req: ProfileUpdateRequest, db: Session = Depends(get_db_session)):
    """Updates or creates student profile."""
    p = create_or_update_student_profile(
        db=db,
        name=req.name,
        course=req.course,
        branch=req.branch,
        year=req.year,
        semester=req.semester
    )
    return {"ok": True, "name": p.name, "course": p.course}


@app.get("/api/subjects", tags=["Academics"])
def list_subjects(db: Session = Depends(get_db_session)):
    """Lists registered subjects and syllabus units."""
    subjs = get_subjects(db)
    return [
        {
            "id": s.id,
            "name": s.name,
            "code": s.code,
            "semester": s.semester,
            "description": s.description,
            "topics": [
                {"id": t.id, "unit": t.unit_number, "name": t.topic_name, "completed": t.is_completed}
                for t in s.topics
            ]
        }
        for s in subjs
    ]


@app.post("/api/subjects", tags=["Academics"])
def add_subject(req: SubjectCreateRequest, db: Session = Depends(get_db_session)):
    """Registers a new course subject."""
    s = create_subject(
        db=db,
        name=req.name,
        code=req.code,
        semester=req.semester,
        description=req.description
    )
    return {"ok": True, "id": s.id, "name": s.name, "code": s.code}


@app.post("/api/subjects/{subject_id}/topics", tags=["Academics"])
def add_subject_topic(subject_id: int, req: TopicCreateRequest, db: Session = Depends(get_db_session)):
    """Adds a syllabus topic to a subject."""
    t = add_topic(db=db, subject_id=subject_id, unit_number=req.unit_number, topic_name=req.topic_name)
    return {"ok": True, "id": t.id, "unit": t.unit_number, "topic_name": t.topic_name}


@app.post("/api/topics/{topic_id}/toggle", tags=["Academics"])
def toggle_topic(topic_id: int, db: Session = Depends(get_db_session)):
    """Toggles syllabus topic completion status."""
    t = toggle_topic_completion(db, topic_id)
    if not t:
        raise HTTPException(status_code=404, detail="Topic not found.")
    return {"ok": True, "id": t.id, "is_completed": t.is_completed}


@app.get("/api/documents", tags=["Materials"])
def list_documents(db: Session = Depends(get_db_session)):
    """Lists uploaded study materials and processing statuses."""
    docs = get_documents(db)
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "size_kb": round(d.file_size / 1024, 1),
            "status": d.status,
            "pages": d.total_pages,
            "chunks": d.total_chunks,
            "subject_id": d.subject_id,
            "created_at": d.created_at.isoformat() if d.created_at else None
        }
        for d in docs
    ]


@app.post("/api/documents/upload", tags=["Materials"])
async def upload_document(
    file: UploadFile = File(...),
    subject_id: int = Form(...),
    unit_number: Optional[int] = Form(None),
    topic_name: Optional[str] = Form(None),
    document_type: str = Form("Lecture Notes"),
    db: Session = Depends(get_db_session)
):
    """Uploads and indexes academic document (PDF, DOCX, TXT, CSV)."""
    file_bytes = await file.read()
    try:
        doc = save_and_process_document(
            db=db,
            file_bytes=file_bytes,
            original_filename=file.filename or "uploaded_file.pdf",
            subject_id=subject_id,
            unit_number=unit_number,
            topic_name=topic_name,
            document_type=document_type
        )
        return {
            "ok": True,
            "document_id": doc.id,
            "filename": doc.filename,
            "status": doc.status,
            "pages": doc.total_pages,
            "chunks": doc.total_chunks
        }
    except Exception as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.delete("/api/documents/{doc_id}", tags=["Materials"])
def delete_document(doc_id: int, db: Session = Depends(get_db_session)):
    """Deletes uploaded document and removes chunks from vector index."""
    deleted = delete_document_with_files(db, doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found.")
    return {"ok": True, "message": f"Document #{doc_id} deleted."}


@app.post("/api/chat", tags=["AI Tutor"])
def chat_with_tutor(req: ChatRequest, db: Session = Depends(get_db_session)):
    """Conversational tutor with RAG retrieval, student memory, and chat persistence."""
    query = req.query.strip()
    if not query:
        raise HTTPException(status_code=400, detail="Query cannot be empty.")

    # Get or create conversation
    conv_id = req.conversation_id
    if not conv_id:
        conv = create_conversation(db=db, title=query[:40], subject_id=req.subject_id)
        conv_id = conv.id

    # Record user message
    add_message(db, conversation_id=conv_id, role="user", content=query)

    # Retrieval Grounding
    v_store = get_vector_store()
    retrieved_passages = []
    citations = []
    if v_store.count() > 0:
        embedder = get_embedding_generator()
        q_vec = embedder.embed_text(query)
        hits = v_store.search(q_vec, top_k=3, filter_subject_id=req.subject_id)
        for h in hits:
            retrieved_passages.append(f"[Page {h.get('page_number', 1)}]: {h.get('content', '')}")
            citations.append({"document_id": str(h.get("document_id")), "page": str(h.get("page_number"))})

    context_block = "\n\n".join(retrieved_passages)
    sys_instruction = (
        "You are ASIP, an intelligent, empathetic AI student tutor and academic copilot. "
        "Ground your answers in the student's uploaded material when relevant. "
        "Provide structured explanations, code snippets, and key takeaways."
    )
    prompt = f"Student Question: {query}\n"
    if context_block:
        prompt += f"\nRelevant study material excerpt:\n{context_block}\n"

    try:
        reply_text, model_name = call_llm(prompt=prompt, system_instruction=sys_instruction)
    except Exception as exc:
        reply_text = f"Tutor response: {safe_user_error(exc)}"
        model_name = "Offline Fallback"

    # Save assistant message
    add_message(
        db,
        conversation_id=conv_id,
        role="assistant",
        content=reply_text,
        agent_name="AI Tutor",
        citations_json=json.dumps(citations)
    )

    return {
        "ok": True,
        "conversation_id": conv_id,
        "reply": reply_text,
        "model": model_name,
        "grounded": bool(context_block),
        "citations": citations
    }


@app.get("/api/conversations", tags=["AI Tutor"])
def list_conversations(db: Session = Depends(get_db_session)):
    """Lists saved conversation sessions."""
    convs = get_conversations(db)
    return [
        {"id": c.id, "title": c.title, "updated_at": c.updated_at.isoformat() if c.updated_at else None}
        for c in convs
    ]


@app.get("/api/conversations/{conv_id}/messages", tags=["AI Tutor"])
def get_conversation_history(conv_id: int, db: Session = Depends(get_db_session)):
    """Retrieves full message history for a conversation."""
    msgs = get_messages(db, conv_id)
    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "agent_name": m.agent_name,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in msgs
    ]


@app.get("/api/goals", tags=["Goals & Tasks"])
def list_goals(db: Session = Depends(get_db_session)):
    """Lists student learning goals and subtasks."""
    goals = get_goals(db)
    return [
        {
            "id": g.id,
            "title": g.title,
            "objective": g.objective,
            "status": g.status,
            "progress": g.progress_percentage,
            "deadline": g.deadline.isoformat() if g.deadline else None,
            "tasks": [
                {
                    "id": t.id,
                    "title": t.title,
                    "agent": t.agent_assigned,
                    "effort_minutes": t.effort_estimate_minutes,
                    "status": t.status,
                    "scheduled_date": str(t.scheduled_date) if t.scheduled_date else None
                }
                for t in g.tasks
            ]
        }
        for g in goals
    ]


@app.post("/api/goals", tags=["Goals & Tasks"])
def create_goal_endpoint(req: GoalCreateRequest, db: Session = Depends(get_db_session)):
    """Decomposes student prompt into a goal with ordered subtasks."""
    goal, tasks = create_goal_and_tasks_from_prompt(
        db=db,
        prompt=f"{req.title}. {req.objective}",
        subject_id=req.subject_id
    )
    return {
        "ok": True,
        "goal_id": goal.id,
        "title": goal.title,
        "tasks_created": len(tasks)
    }


@app.post("/api/tasks/{task_id}/toggle", tags=["Goals & Tasks"])
def toggle_task(task_id: int, db: Session = Depends(get_db_session)):
    """Toggles subtask completion."""
    task = toggle_task_completion(db, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found.")
    return {"ok": True, "task_id": task.id, "status": task.status}


@app.post("/api/orchestrate", tags=["Multi-Agent"])
def orchestrate_agents(req: OrchestrateRequest, db: Session = Depends(get_db_session)):
    """Multi-Agent Orchestrator: routes goal to specialists with full execution trace."""
    res = route_request(db=db, query=req.query, extra={"subject_id": req.subject_id})
    return {
        "ok": True,
        "query": res.query,
        "intents": res.intents,
        "combined_summary": res.combined_summary,
        "plan": res.plan,
        "agent_run_id": res.agent_run_id,
        "evaluation": {
            "overall_score": res.evaluation.overall_score if res.evaluation else 1.0,
            "feedback": res.evaluation.feedback if res.evaluation else "Verified."
        } if res.evaluation else None,
        "trace": [
            {
                "step_id": t.step_id,
                "stage": t.stage,
                "agent": t.agent_name,
                "action": t.action_description,
                "time": t.timestamp
            }
            for t in res.execution_trace
        ]
    }


@app.get("/api/agents/runs", tags=["Multi-Agent"])
def list_agent_runs(limit: int = 20, db: Session = Depends(get_db_session)):
    """Lists agent run history and execution traces."""
    runs = get_agent_runs(db, limit=limit)
    return [
        {
            "id": r.id,
            "agent_name": r.agent_name,
            "input_query": r.input_query,
            "status": r.status,
            "started_at": r.started_at.isoformat() if r.started_at else None,
            "finished_at": r.finished_at.isoformat() if r.finished_at else None,
            "output_preview": r.output_result[:200] if r.output_result else "",
            "tool_calls_count": len(r.tool_calls)
        }
        for r in runs
    ]


@app.get("/api/tools", tags=["Tools"])
def list_tools():
    """Lists registered safe tools and their schemas."""
    return get_tool_registry().list_tools()


@app.post("/api/tools/execute", tags=["Tools"])
def execute_tool_endpoint(req: ToolExecuteRequest, db: Session = Depends(get_db_session)):
    """Executes a registered tool directly with safety validation and audit logging."""
    reg = get_tool_registry()
    out = reg.execute_tool(req.tool_name, req.arguments, db=db)
    return out


@app.post("/api/autonomous/prepare", tags=["Autonomous Pipeline"])
def autonomous_prepare(req: AutonomousPrepRequest, db: Session = Depends(get_db_session)):
    """Executes the complete 15-step autonomous exam preparation pipeline."""
    coord = AutonomousLearningCoordinator(db=db)
    res = coord.run_full_preparation_workflow(prompt=req.goal_prompt, subject_id=req.subject_id)
    return res


@app.get("/api/analytics/performance", tags=["Analytics"])
def get_performance_analytics(db: Session = Depends(get_db_session)):
    """Calculates student accuracy trends, attempts, and difficulty distributions."""
    return compute_performance(db)


@app.get("/api/analytics/weaknesses", tags=["Analytics"])
def get_weaknesses(db: Session = Depends(get_db_session)):
    """Detects academic weaknesses requiring reinforcement."""
    return detect_weak_topics(db)


@app.get("/api/analytics/knowledge-map", tags=["Analytics"])
def get_knowledge_map(subject_id: Optional[int] = Query(None), db: Session = Depends(get_db_session)):
    """Returns knowledge graph / topic map with nodes and edges."""
    return generate_knowledge_map(db=db, subject_id=subject_id)


@app.get("/api/memory", tags=["Memory"])
def list_student_memories(db: Session = Depends(get_db_session)):
    """Lists stored student learning memories and preferences."""
    mems = get_memories(db)
    return [
        {
            "id": m.id,
            "key": m.key,
            "value": m.value,
            "memory_type": m.memory_type,
            "importance": m.importance,
            "created_at": m.created_at.isoformat() if m.created_at else None
        }
        for m in mems
    ]


@app.post("/api/memory", tags=["Memory"])
def create_student_memory(req: MemoryCreateRequest, db: Session = Depends(get_db_session)):
    """Saves a student preference or learning context item."""
    m = save_memory(
        db=db,
        key=req.key,
        value=req.value,
        memory_type=req.memory_type,
        importance=req.importance
    )
    return {"ok": True, "id": m.id, "key": m.key}


@app.delete("/api/memory/{memory_id}", tags=["Memory"])
def delete_student_memory(memory_id: int, db: Session = Depends(get_db_session)):
    """Removes a student memory record."""
    deleted = delete_memory(db, memory_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Memory not found.")
    return {"ok": True, "message": "Memory deleted."}


@app.get("/api/reports/readiness", tags=["Reports"])
def get_readiness_report(subject_id: Optional[int] = Query(None), db: Session = Depends(get_db_session)):
    """Generates an academic readiness report in Markdown and HTML."""
    return generate_exam_readiness_report(db=db, subject_id=subject_id)


@app.get("/api/diagnostics", tags=["System"])
def get_diagnostics(db: Session = Depends(get_db_session)):
    """Developer and diagnostics telemetry."""
    settings.reload()
    v_store = get_vector_store()
    diag = get_gemini_diagnostics()
    return {
        "system": "OK",
        "app_name": settings.APP_NAME,
        "app_env": settings.APP_ENV,
        "gemini_configured": diag["gemini_configured"],
        "gemini_connection": diag["gemini_connection"],
        "active_provider": diag["active_provider"],
        "active_model": diag["active_model"],
        "database_url": settings.DATABASE_URL.split("///")[-1],
        "vector_store_path": str(settings.VECTOR_STORE_PATH),
        "total_vector_chunks": v_store.count(),
        "registered_tools": [t["name"] for t in get_tool_registry().list_tools()],
        "server_time": datetime.now(timezone.utc).isoformat()
    }


# Root route: provides informative API entry point and link to interactive docs
@app.get("/", response_class=HTMLResponse, tags=["System"])
def root_index():
    return """<!DOCTYPE html>
<html>
<head>
    <title>ASIP - Autonomous Student Intelligence Platform</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0F172A; color: #F8FAFC; margin: 0; padding: 40px; }
        .card { background: #1E293B; border-radius: 12px; padding: 32px; max-width: 800px; margin: auto; box-shadow: 0 10px 25px rgba(0,0,0,0.5); }
        h1 { color: #38BDF8; margin-top: 0; }
        a { color: #38BDF8; text-decoration: none; font-weight: bold; }
        .badge { background: #0284C7; color: white; padding: 4px 10px; border-radius: 20px; font-size: 0.8rem; font-weight: bold; }
        .btn { display: inline-block; background: #2563EB; color: white; padding: 10px 20px; border-radius: 8px; text-decoration: none; margin-top: 15px; font-weight: 600; }
        .btn:hover { background: #1D4ED8; }
        ul { line-height: 1.8; }
    </style>
</head>
<body>
    <div class="card">
        <span class="badge">ASIP 2.0 • Autonomous Multi-Agent</span>
        <h1>🎓 Autonomous Student Intelligence Platform</h1>
        <p>A functional AGI-inspired autonomous academic platform combining planning, reasoning, memory, tool use, multiple specialist agents, self-evaluation, and adaptive task execution.</p>
        
        <h3>⚡ Quick Navigation</h3>
        <ul>
            <li><strong>Swagger API Interactive Docs:</strong> <a href="/docs">/docs</a></li>
            <li><strong>ReDoc Alternative Documentation:</strong> <a href="/redoc">/redoc</a></li>
            <li><strong>System Diagnostics & Telemetry:</strong> <a href="/api/diagnostics">/api/diagnostics</a></li>
            <li><strong>System Health:</strong> <a href="/api/health">/api/health</a></li>
        </ul>

        <a href="/docs" class="btn">Explore OpenAPI Swagger UI</a>
    </div>
</body>
</html>
"""
