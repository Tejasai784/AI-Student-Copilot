"""Master AGI Controller & Multi-Agent Orchestrator.
Coordinates the full execution graph / state machine:
USER GOAL -> CONTROLLER -> PLAN -> SPECIALIST AGENTS -> TOOL CALLS -> RESULTS -> CRITIC -> RETRY/REVISE -> FINAL RESPONSE -> MEMORY UPDATE.
Logs full explainable execution trace to AgentRun, ToolCall, and Evaluation tables.
"""
from __future__ import annotations

import re
import json
from datetime import datetime, timezone
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session

from agents.contracts import (
    AgentRequest,
    AgentResult,
    OrchestratorResult,
    ExecutionTraceStep,
    ToolExecutionStep
)
from agents.planner_agent import run_planner_agent
from agents.study_agent import run_study_agent
from agents.coding_agent import run_coding_agent
from agents.math_agent import run_math_agent
from agents.research_agent import run_research_agent
from agents.exam_agent import run_exam_agent
from agents.memory_agent import run_memory_agent
from agents.critic_agent import evaluate_output_quality, run_critic_agent
from database.crud import (
    create_agent_run,
    finish_agent_run,
    get_subjects,
    get_documents,
    save_memory
)
from backend.logging_config import logger


INTENT_PATTERNS = [
    ("coding", re.compile(r"\b(code|python|java|c\+\+|function|debug|algorithm|script|programming|implement)\b", re.I)),
    ("math", re.compile(r"\b(math|calculat|solve|integral|derivative|matrix|formula|equation|sqrt)\b", re.I)),
    ("research", re.compile(r"\b(research|citation|reference|source|documented|proof|verify)\b", re.I)),
    ("exam", re.compile(r"\b(practice question|quiz|mcq|exam question|mock test|test me|generate question)\b", re.I)),
    ("planner", re.compile(r"\b(study plan|schedule|timetable|planner|revision plan|prepare in|prepare me)\b", re.I)),
    ("study", re.compile(r"\b(explain|what is|define|teach|tutor|help me understand|summary|notes|flashcard)\b", re.I)),
]


def detect_capabilities(query: str) -> List[str]:
    """Detects required specialist capabilities from user query."""
    intents = []
    for name, pattern in INTENT_PATTERNS:
        if pattern.search(query or "") and name not in intents:
            intents.append(name)
    if not intents:
        intents = ["study"]
    return intents


def match_subject_in_db(db: Session, query: str) -> Tuple[Optional[int], Optional[str]]:
    """Matches query to registered subjects in the database."""
    subjects = get_subjects(db)
    q = (query or "").lower()
    for subj in subjects:
        if subj.name.lower() in q or subj.code.lower() in q:
            return subj.id, subj.name
        initials = "".join(w[0] for w in subj.name.split() if w[:1].isalpha())
        if len(initials) >= 3 and initials.lower() in q.replace(" ", ""):
            return subj.id, subj.name
    return None, None


def route_request(db: Session, query: str, extra: Optional[dict] = None) -> OrchestratorResult:
    """
    Main AGI Controller execution engine.
    Executes the structured State Machine with audit logging and full UI trace.
    """
    extra = extra or {}
    subject_id, subject_name = match_subject_in_db(db, query)
    if extra.get("subject_id"):
        subject_id = extra["subject_id"]

    capabilities = detect_capabilities(query)
    # Always include memory agent for long-term context
    all_intents = list(capabilities)

    # 1. State Machine: Stage 1 - Ingestion & Planning
    plan_steps = [f"Analyze intent and match subject (matched: {subject_name or 'General'})"]
    for cap in capabilities:
        plan_steps.append(f"Delegate subtask to {cap.capitalize()} Agent")
    plan_steps.append("Invoke Evaluation & Critic Agent for consistency and rubric check")
    plan_steps.append("Update student long-term memory")

    # Create AgentRun record in DB
    agent_run = create_agent_run(
        db=db,
        agent_name="AGI Controller",
        input_query=query,
        plan_json=json.dumps(plan_steps)
    )
    agent_run_id = agent_run.id

    trace: List[ExecutionTraceStep] = []
    step_num = 1

    def add_trace(stage: str, agent: str, action: str, details: Dict[str, Any]):
        nonlocal step_num
        trace.append(ExecutionTraceStep(
            step_id=step_num,
            stage=stage,
            agent_name=agent,
            action_description=action,
            details=details,
            timestamp=datetime.now(timezone.utc).strftime("%H:%M:%S")
        ))
        step_num += 1

    add_trace("Goal", "AGI Controller", f"Received student goal: '{query[:80]}'", {"intents": capabilities})
    add_trace("Plan", "AGI Controller", f"Formulated execution plan with {len(capabilities)} specialists", {"plan": plan_steps})

    # Prepare common request
    req = AgentRequest(
        query=query,
        subject_id=subject_id,
        unit_number=extra.get("unit_number"),
        topic_name=extra.get("topic_name"),
        extra=extra,
        user_id=extra.get("user_id")
    )

    # 2. State Machine: Stage 2 - Execute Specialist Agents
    agent_results: List[AgentResult] = []

    # Inject Memory first if applicable
    mem_result = run_memory_agent(db, req, agent_run_id=agent_run_id)
    agent_results.append(mem_result)
    add_trace("Agent", "Memory Agent", "Retrieved student memory and context", {"total_memories": mem_result.data.get("total_memories")})

    # Ordered execution of specialists
    for cap in capabilities:
        res = None
        if cap == "planner":
            res = run_planner_agent(db, req, agent_run_id=agent_run_id)
        elif cap == "study":
            res = run_study_agent(req, db=db, agent_run_id=agent_run_id)
        elif cap == "coding":
            res = run_coding_agent(req, db=db, agent_run_id=agent_run_id)
        elif cap == "math":
            res = run_math_agent(req, db=db, agent_run_id=agent_run_id)
        elif cap == "research":
            res = run_research_agent(req, db=db, agent_run_id=agent_run_id)
        elif cap == "exam":
            res = run_exam_agent(db, req, agent_run_id=agent_run_id)

        if res:
            agent_results.append(res)
            # Log any tool executions that occurred
            for tc in res.tool_calls:
                add_trace("Tool", res.agent, f"Called tool '{tc.tool_name}' ({tc.status})", {
                    "arguments": tc.arguments,
                    "duration_ms": tc.execution_time_ms
                })
            add_trace("Result", res.agent, res.summary, {"ok": res.ok})

    # 3. State Machine: Stage 3 - Combine Initial Outputs
    combined_sections = []
    if subject_name:
        combined_sections.append(f"**Target Subject:** {subject_name}\n")

    for r in agent_results:
        if r.agent == "Memory Agent":
            continue
        status_icon = "✅" if r.ok else "⚠️"
        combined_sections.append(f"### {status_icon} {r.agent}\n{r.summary}\n")
        # Include detailed text if present
        for key in ("explanation", "response", "solution", "research_summary"):
            if key in r.data and r.data[key]:
                combined_sections.append(str(r.data[key]))
                break

    initial_output = "\n\n".join(combined_sections)

    # 4. State Machine: Stage 4 - Critic & Evaluation Check
    critic_eval = evaluate_output_quality(
        query=query,
        combined_response=initial_output,
        agent_results=agent_results,
        db=db,
        agent_run_id=agent_run_id
    )
    add_trace("Critic", "Evaluation & Critic Agent", f"Quality Assessment: {int(critic_eval.overall_score * 100)}/100", {
        "score": critic_eval.overall_score,
        "retry_required": critic_eval.retry_required,
        "feedback": critic_eval.feedback
    })

    # 5. State Machine: Stage 5 - Controlled Retry / Revision Loop
    final_output = initial_output
    retry_count = 0
    if critic_eval.retry_required and retry_count < 1:
        retry_count = 1
        add_trace("Revision", "AGI Controller", "Executing targeted revision to address quality gaps", {"notes": critic_eval.revision_notes})
        # Re-run study agent with emphasis on query completeness
        revised_res = run_study_agent(req, db=db, agent_run_id=agent_run_id)
        if revised_res.ok and "explanation" in revised_res.data:
            final_output += f"\n\n### 🔄 Revised Academic Synthesis\n{revised_res.data['explanation']}"
            add_trace("Revision", "Study Agent", "Generated expanded conceptual synthesis", {})

    # 6. State Machine: Stage 6 - Final Response & Memory Update
    add_trace("Final", "AGI Controller", "Orchestrated final response and saved learning state", {
        "execution_steps": len(trace) + 1,
        "agent_run_id": agent_run_id
    })

    # Save summary to student memory
    save_memory(
        db=db,
        key=f"goal_run_{agent_run_id}",
        value=f"Completed study session on '{query[:80]}' with {len(capabilities)} agents.",
        memory_type="context",
        importance=3,
        user_id=req.user_id
    )

    # Convert trace to serializable list for DB
    trace_serializable = [
        {
            "step_id": t.step_id,
            "stage": t.stage,
            "agent_name": t.agent_name,
            "action": t.action_description,
            "details": t.details,
            "time": t.timestamp
        }
        for t in trace
    ]

    finish_agent_run(
        db=db,
        run_id=agent_run_id,
        status="SUCCESS",
        output_result=final_output[:4000],
        execution_trace_json=json.dumps(trace_serializable),
        retry_count=retry_count
    )

    return OrchestratorResult(
        query=query,
        intents=capabilities,
        combined_summary=final_output,
        plan=plan_steps,
        results=agent_results,
        evaluation=critic_eval,
        execution_trace=trace,
        subject_id=subject_id,
        agent_run_id=agent_run_id,
        status="SUCCESS"
    )
