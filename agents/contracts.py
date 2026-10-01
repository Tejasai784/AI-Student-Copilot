"""Structured contracts between agents, tools, and the orchestrator."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class ToolExecutionStep:
    tool_name: str
    arguments: Dict[str, Any]
    output: Dict[str, Any]
    execution_time_ms: float = 0.0
    status: str = "SUCCESS"


@dataclass
class AgentRequest:
    query: str
    subject_id: Optional[int] = None
    unit_number: Optional[int] = None
    topic_name: Optional[str] = None
    extra: Dict[str, Any] = field(default_factory=dict)
    conversation_id: Optional[int] = None
    user_id: Optional[int] = None


@dataclass
class AgentResult:
    agent: str
    ok: bool
    summary: str
    data: Dict[str, Any] = field(default_factory=dict)
    tool_calls: List[ToolExecutionStep] = field(default_factory=list)
    citations: List[Dict[str, str]] = field(default_factory=list)
    error: Optional[str] = None


@dataclass
class CriticEvaluationResult:
    factual_consistency: float  # 0.0 - 1.0
    completeness: float         # 0.0 - 1.0
    relevance: float            # 0.0 - 1.0
    overall_score: float        # 0.0 - 1.0
    feedback: str
    groundedness: float = 1.0   # 0.0 - 1.0
    retry_required: bool = False
    revision_notes: Optional[str] = None


@dataclass
class ExecutionTraceStep:
    step_id: int
    stage: str                  # Goal | Plan | Agent | Tool | Result | Critic | Revision | Final
    agent_name: str
    action_description: str
    tool_used: Optional[str] = None
    duration_ms: float = 0.0
    parent_step_id: Optional[int] = None
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = ""


@dataclass
class OrchestratorResult:
    query: str
    intents: List[str]
    combined_summary: str
    plan: List[str] = field(default_factory=list)
    results: List[AgentResult] = field(default_factory=list)
    evaluation: Optional[CriticEvaluationResult] = None
    execution_trace: List[ExecutionTraceStep] = field(default_factory=list)
    subject_id: Optional[int] = None
    agent_run_id: Optional[int] = None
    status: str = "SUCCESS"
