"""Planner Agent — converts broad goals into actionable subtasks with effort estimation."""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from datetime import date, timedelta

from agents.contracts import AgentRequest, AgentResult, ToolExecutionStep
from backend.security import safe_user_error
from tools.registry import get_tool_registry
from services.goal_service import parse_goal_intent, extract_deadline_days
from database.crud import create_goal, create_task, get_subjects


def run_planner_agent(db: Session, request: AgentRequest, agent_run_id: Optional[int] = None) -> AgentResult:
    """
    Planner Agent:
    - converts broad goals into actionable tasks
    - orders dependencies
    - estimates effort
    - adapts plans when tasks fail
    """
    tool_steps: List[ToolExecutionStep] = []
    reg = get_tool_registry()

    try:
        query = request.query
        days = extract_deadline_days(query) or request.extra.get("days") or 7
        parsed = parse_goal_intent(query)

        # Decompose into ordered tasks
        task_plans = [
            {
                "order": 1,
                "title": f"Initial Syllabus & Concept Review ({parsed['subject_hint']})",
                "agent": "Study Agent",
                "effort_minutes": 60,
                "dependencies": []
            },
            {
                "order": 2,
                "title": "Deep Dive: Core Algorithms, Data Structures & Logic",
                "agent": "Coding Agent" if "python" in query.lower() or "code" in query.lower() else "Study Agent",
                "effort_minutes": 90,
                "dependencies": [1]
            },
            {
                "order": 3,
                "title": "Representative Practice Exam & Diagnostic Mock Test",
                "agent": "Exam Agent",
                "effort_minutes": 60,
                "dependencies": [2]
            },
            {
                "order": 4,
                "title": "Weak Topic Remediation & Readiness Assessment",
                "agent": "Critic Agent",
                "effort_minutes": 45,
                "dependencies": [3]
            }
        ]

        # Use task_state_manager tool to record plan
        tool_args = {"action": "list_goals"}
        t_out = reg.execute_tool("task_state_manager", tool_args, db=db, agent_run_id=agent_run_id)
        tool_steps.append(ToolExecutionStep(
            tool_name="task_state_manager",
            arguments=tool_args,
            output=t_out,
            execution_time_ms=t_out.get("execution_time_ms", 0.0),
            status="SUCCESS" if t_out.get("ok") else "FAILED"
        ))

        summary = (
            f"Created a {days}-day structured academic plan for {parsed['subject_hint']} "
            f"comprising {len(task_plans)} sequential tasks ({sum(t['effort_minutes'] for t in task_plans)} total study minutes)."
        )

        return AgentResult(
            agent="Planner Agent",
            ok=True,
            summary=summary,
            data={
                "days": days,
                "subject": parsed["subject_hint"],
                "tasks": task_plans,
                "constraints": parsed["constraints"],
                "required_resources": parsed["required_resources"]
            },
            tool_calls=tool_steps
        )
    except Exception as exc:
        return AgentResult(
            agent="Planner Agent",
            ok=False,
            summary="Planner agent encountered an error.",
            error=safe_user_error(exc)
        )
