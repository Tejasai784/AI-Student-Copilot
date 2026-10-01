"""Multi-agent orchestrator, specialist agents, and autonomous workflow router."""
from __future__ import annotations

import json
from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import ApiResponse
from database.models import User, AgentRun, ToolCall
from database.crud import get_agent_runs
from agents.orchestrator import route_request
from services.autonomous_workflow import AutonomousLearningCoordinator
from tools.registry import get_tool_registry

router = APIRouter(prefix="/api/v1/agents", tags=["Multi-Agent Orchestration"])


class OrchestrateRequest(BaseModel):
    query: str = Field(..., min_length=3)
    subject_id: Optional[int] = None


class AutonomousPrepRequest(BaseModel):
    goal_prompt: str = Field(..., min_length=5)
    subject_id: Optional[int] = None


class ToolExecuteRequest(BaseModel):
    tool_name: str
    arguments: Dict[str, Any] = {}


@router.post("/orchestrate", response_model=ApiResponse[Dict[str, Any]])
def orchestrate_request_endpoint(
    req: OrchestrateRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Routes an academic request through the multi-agent orchestrator with execution trace."""
    res = route_request(db=db, query=req.query, extra={"subject_id": req.subject_id})
    data = {
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
    return ApiResponse(success=True, data=data)


@router.post("/autonomous/prepare", response_model=ApiResponse[Dict[str, Any]])
def run_autonomous_preparation(
    req: AutonomousPrepRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Executes the autonomous multi-agent preparation pipeline for a goal."""
    coord = AutonomousLearningCoordinator(db=db)
    res = coord.run_full_preparation_workflow(prompt=req.goal_prompt, subject_id=req.subject_id)
    return ApiResponse(success=True, data=res)


@router.get("/runs", response_model=ApiResponse[List[Dict[str, Any]]])
def list_agent_runs_endpoint(
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Lists past agent execution runs and traces."""
    runs = get_agent_runs(db, limit=limit)
    data = [
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
    return ApiResponse(success=True, data=data)


@router.get("/runs/{run_id}", response_model=ApiResponse[Dict[str, Any]])
def get_agent_run_detail(
    run_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves full details and tool calls for a specific agent execution run."""
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent run not found.")

    tool_calls = [
        {
            "id": tc.id,
            "tool_name": tc.tool_name,
            "status": tc.status,
            "execution_time_ms": tc.execution_time_ms,
            "tool_input": tc.tool_input_json,
            "tool_output": tc.tool_output_json,
            "created_at": tc.created_at.isoformat() if tc.created_at else None
        }
        for tc in run.tool_calls
    ]

    data = {
        "id": run.id,
        "agent_name": run.agent_name,
        "input_query": run.input_query,
        "status": run.status,
        "output_result": run.output_result,
        "plan_json": run.plan_json,
        "execution_trace_json": run.execution_trace_json,
        "error_message": run.error_message,
        "started_at": run.started_at.isoformat() if run.started_at else None,
        "finished_at": run.finished_at.isoformat() if run.finished_at else None,
        "tool_calls": tool_calls
    }
    return ApiResponse(success=True, data=data)


@router.get("/tools", response_model=ApiResponse[List[Dict[str, Any]]])
def list_available_tools():
    """Lists registered safe tools and their schemas."""
    tools = get_tool_registry().list_tools()
    return ApiResponse(success=True, data=tools)


@router.post("/tools/execute", response_model=ApiResponse[Dict[str, Any]])
def execute_tool(
    req: ToolExecuteRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Directly executes a tool with safety checks and logging."""
    reg = get_tool_registry()
    out = reg.execute_tool(req.tool_name, req.arguments, db=db)
    return ApiResponse(success=True, data=out)
