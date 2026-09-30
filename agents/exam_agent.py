"""Exam Agent — generates questions, mock tests, evaluates answers, and identifies weak topics."""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from agents.contracts import AgentRequest, AgentResult, ToolExecutionStep
from backend.security import safe_user_error
from tools.registry import get_tool_registry
from database.crud import get_subjects, get_subject_by_id


def run_exam_agent(db: Session, request: AgentRequest, agent_run_id: Optional[int] = None) -> AgentResult:
    tool_steps: List[ToolExecutionStep] = []
    reg = get_tool_registry()

    try:
        query = request.query
        subject_name = "Course Material"
        if "python" in query.lower():
            subject_name = "Python Programming"
        elif "dbms" in query.lower() or "database" in query.lower():
            subject_name = "Database Management Systems"
        elif request.subject_id:
            subj = get_subject_by_id(db, request.subject_id)
            if subj:
                subject_name = subj.name
        else:
            subjects = get_subjects(db)
            if subjects:
                subject_name = subjects[0].name

        # Execute quiz_generator tool
        tool_args = {
            "topic": subject_name,
            "num_questions": 3,
            "difficulty": "medium"
        }
        quiz_out = reg.execute_tool("quiz_generator", tool_args, db=db, agent_run_id=agent_run_id)
        tool_steps.append(ToolExecutionStep(
            tool_name="quiz_generator",
            arguments=tool_args,
            output=quiz_out,
            execution_time_ms=quiz_out.get("execution_time_ms", 0.0),
            status="SUCCESS" if quiz_out.get("ok") else "FAILED"
        ))

        questions = quiz_out.get("questions", [])

        summary = (
            f"Generated diagnostic assessment with {len(questions)} questions "
            f"covering {subject_name} with answer keys and scoring rubrics."
        )

        return AgentResult(
            agent="Exam Agent",
            ok=True,
            summary=summary,
            data={
                "subject": subject_name,
                "total_questions": len(questions),
                "questions": questions
            },
            tool_calls=tool_steps
        )
    except Exception as exc:
        return AgentResult(
            agent="Exam Agent",
            ok=False,
            summary="Exam agent encountered an error.",
            error=safe_user_error(exc)
        )
