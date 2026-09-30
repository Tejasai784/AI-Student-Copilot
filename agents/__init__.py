"""Multi-Agent Architecture for ASIP."""
from agents.contracts import (
    AgentRequest,
    AgentResult,
    OrchestratorResult,
    ExecutionTraceStep,
    ToolExecutionStep,
    CriticEvaluationResult
)
from agents.orchestrator import route_request, detect_capabilities
from agents.planner_agent import run_planner_agent
from agents.study_agent import run_study_agent
from agents.coding_agent import run_coding_agent
from agents.math_agent import run_math_agent
from agents.research_agent import run_research_agent
from agents.exam_agent import run_exam_agent
from agents.memory_agent import run_memory_agent
from agents.critic_agent import run_critic_agent, evaluate_output_quality

__all__ = [
    "AgentRequest",
    "AgentResult",
    "OrchestratorResult",
    "ExecutionTraceStep",
    "ToolExecutionStep",
    "CriticEvaluationResult",
    "route_request",
    "detect_capabilities",
    "run_planner_agent",
    "run_study_agent",
    "run_coding_agent",
    "run_math_agent",
    "run_research_agent",
    "run_exam_agent",
    "run_memory_agent",
    "run_critic_agent",
    "evaluate_output_quality"
]
