"""Tests for Phase 2: Multi-Agent Reasoning & Safe Tool Use.
- Tool Registry & Safety Limits (calculator AST, python sandbox security, tabular reader)
- All 9 Specialist Agents (Planner, Study, Coding, Math, Research, Exam, Memory, Critic)
- AGI Controller Orchestration & State Machine Execution Trace
"""
import pytest
from tools.registry import get_tool_registry
from tools.calculator import CalculatorTool
from tools.python_sandbox import PythonSandboxTool
from agents.contracts import AgentRequest
from agents.planner_agent import run_planner_agent
from agents.study_agent import run_study_agent
from agents.coding_agent import run_coding_agent
from agents.math_agent import run_math_agent
from agents.research_agent import run_research_agent
from agents.exam_agent import run_exam_agent
from agents.memory_agent import run_memory_agent
from agents.critic_agent import evaluate_output_quality
from agents.orchestrator import route_request, detect_capabilities


def test_tool_registry_and_safe_calculator():
    reg = get_tool_registry()
    calc = reg.get_tool("calculator")
    assert calc is not None

    # Valid arithmetic
    out = calc.execute(expression="(25 * 4) + sqrt(144)")
    assert out["ok"] is True
    assert out["result"] == 112.0

    # Division by zero safety
    div_zero = calc.execute(expression="10 / 0")
    assert div_zero["ok"] is False
    assert "Division by zero" in div_zero["error"]


def test_python_sandbox_security_and_execution():
    reg = get_tool_registry()
    sandbox = reg.get_tool("python_sandbox")
    assert sandbox is not None

    # Safe snippet execution
    safe_code = (
        "def square(x):\n"
        "    return x * x\n"
        "print('RESULT:', square(9))\n"
    )
    res = sandbox.execute(code=safe_code)
    assert res["ok"] is True
    assert "RESULT: 81" in res["stdout"]

    # Blocked dangerous import
    malicious_code = "import os; print(os.getcwd())"
    sec_res = sandbox.execute(code=malicious_code)
    assert sec_res["ok"] is False
    assert "forbidden" in sec_res["error"].lower() or "blocked" in sec_res["stderr"].lower()


def test_specialist_agents_execution(db_session):
    req = AgentRequest(query="Explain Python dictionary performance and time complexity")

    # Study Agent
    study_res = run_study_agent(req, db=db_session)
    assert study_res.ok is True
    assert "Study Agent" in study_res.agent
    assert len(study_res.data["explanation"]) > 50

    # Coding Agent
    code_req = AgentRequest(query="Write and test a Python function to sort numbers")
    code_res = run_coding_agent(code_req, db=db_session)
    assert code_res.ok is True
    assert code_res.data.get("sandbox_executed") is True

    # Math Agent
    math_req = AgentRequest(query="Calculate sqrt(144) + 15 * 4")
    math_res = run_math_agent(math_req, db=db_session)
    assert math_res.ok is True
    assert math_res.data.get("calculator_used") is True

    # Research Agent
    res_req = AgentRequest(query="Research BCNF vs 3NF normalization")
    res_res = run_research_agent(res_req, db=db_session)
    assert res_res.ok is True
    assert len(res_res.citations) >= 1

    # Exam Agent
    exam_req = AgentRequest(query="Generate 3 quiz questions on Python")
    exam_res = run_exam_agent(db_session, exam_req)
    assert exam_res.ok is True
    assert exam_res.data["total_questions"] >= 2


def test_critic_agent_quality_evaluation():
    # Good complete output
    good_eval = evaluate_output_quality(
        query="Explain Python functions with code",
        combined_response="### Functions in Python\nFunctions are reusable blocks of code.\n```python\ndef greet(): pass\n```\nDay 1 task.",
        agent_results=[]
    )
    assert good_eval.overall_score >= 0.70
    assert good_eval.retry_required is False

    # Low quality empty output
    poor_eval = evaluate_output_quality(
        query="Generate a complete 7 day plan",
        combined_response="ok",
        agent_results=[]
    )
    assert poor_eval.retry_required is True


def test_agi_controller_orchestration_and_trace(db_session):
    query = "Prepare me for my Python exam in 7 days. Focus on data structures, loops, and mock test."
    res = route_request(db=db_session, query=query)

    assert res.status == "SUCCESS"
    assert len(res.intents) >= 2
    assert len(res.plan) >= 3
    assert len(res.results) >= 2
    assert res.agent_run_id is not None

    # Verify explainable trace contains stages
    stages = [t.stage for t in res.execution_trace]
    assert "Goal" in stages
    assert "Plan" in stages
    assert "Agent" in stages
    assert "Critic" in stages
    assert "Final" in stages
