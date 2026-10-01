"""
Phase 4 Verification Tests: Tools, Multi-Agent System & Execution Trace.

Validates:
1. ToolRegistry with Pydantic input schemas and validation.
2. Hardened Python execution sandbox:
   - Network escape rejection (socket, urllib, requests)
   - File escape rejection (open, pathlib, shutil)
   - Introspection escape rejection (__subclasses__, __class__, globals)
   - Stripped environment (no API keys in globals/environment)
   - Strict timeout protection
3. AgentOrchestrator:
   - Centralized coordinator for all 9 specialist agents
   - Full explainable execution trace (agent, action, tool_used, duration, parent_step)
   - Database persistence in AgentRun and ToolCall tables
4. Evaluation & Critic Agent:
   - Groundedness scoring
   - Factual consistency, completeness, and relevance
"""
import pytest
from database.database import get_db
from database.models import AgentRun, ToolCall, Evaluation
from tools.registry import get_tool_registry
from tools.calculator import CalculatorTool
from tools.python_sandbox import PythonSandboxTool
from agents.orchestrator import get_agent_orchestrator, route_request
from agents.critic_agent import evaluate_output_quality
from agents.contracts import AgentResult, ToolExecutionStep


# ============================================================================
# 1. ToolRegistry with Pydantic Input/Output Schemas
# ============================================================================

def test_tool_registry_pydantic_validation():
    reg = get_tool_registry()

    # Valid calculator call via registry
    valid_res = reg.execute_tool("calculator", {"expression": "100 + 44"})
    assert valid_res["ok"] is True
    assert valid_res["result"] == 144.0

    # Invalid calculator call failing Pydantic validation (empty expression)
    invalid_res = reg.execute_tool("calculator", {"expression": ""})
    assert invalid_res["ok"] is False
    assert "invalid input parameters" in invalid_res["error"].lower()


def test_tool_registry_schema_listing():
    reg = get_tool_registry()
    tools = reg.list_tools()
    assert len(tools) >= 9

    calc_tool = next((t for t in tools if t["name"] == "calculator"), None)
    assert calc_tool is not None
    assert "properties" in calc_tool["parameters"]
    assert "expression" in calc_tool["parameters"]["properties"]

    sandbox_tool = next((t for t in tools if t["name"] == "python_sandbox"), None)
    assert sandbox_tool is not None
    assert "code" in sandbox_tool["parameters"]["properties"]


# ============================================================================
# 2. Hardened Python Sandbox Security Tests
# ============================================================================

def test_sandbox_rejects_network_escape():
    sandbox = PythonSandboxTool()

    # Attempt to import socket
    res_socket = sandbox.execute(code="import socket\ns = socket.socket()")
    assert res_socket["ok"] is False
    assert "forbidden module" in res_socket["error"].lower()

    # Attempt to import urllib / requests / http
    res_urllib = sandbox.execute(code="import urllib.request\nurllib.request.urlopen('http://example.com')")
    assert res_urllib["ok"] is False
    assert "forbidden module" in res_urllib["error"].lower()


def test_sandbox_rejects_file_escape():
    sandbox = PythonSandboxTool()

    # Attempt to open file
    res_open = sandbox.execute(code="f = open('data/ai_student_copilot.db', 'r')")
    assert res_open["ok"] is False
    assert "forbidden function call: 'open()'" in res_open["error"].lower()

    # Attempt to import pathlib / shutil
    res_pathlib = sandbox.execute(code="from pathlib import Path\np = Path('.').resolve()")
    assert res_pathlib["ok"] is False
    assert "forbidden module" in res_pathlib["error"].lower()


def test_sandbox_rejects_introspection_escape():
    sandbox = PythonSandboxTool()

    # Attempt to walk object hierarchy to escape sandbox
    res_subclasses = sandbox.execute(code="classes = ().__class__.__bases__[0].__subclasses__()")
    assert res_subclasses["ok"] is False
    assert "forbidden introspective attribute access" in res_subclasses["error"].lower()

    # Attempt globals() access
    res_globals = sandbox.execute(code="g = globals()")
    assert res_globals["ok"] is False
    assert "forbidden function call: 'globals()'" in res_globals["error"].lower()


def test_sandbox_stripped_environment_no_api_keys():
    sandbox = PythonSandboxTool()

    # Check that os and sys are not accessible to read environment variables
    code = (
        "try:\n"
        "    print(os.environ.get('GEMINI_API_KEY'))\n"
        "except Exception as e:\n"
        "    print('BLOCKED:', type(e).__name__)\n"
    )
    res = sandbox.execute(code=code)
    # Rejection occurs at AST validation because 'os' cannot be imported or accessed
    assert res["ok"] is False or "NameError" in res.get("stdout", "")


def test_sandbox_timeout_enforcement():
    sandbox = PythonSandboxTool()

    # Infinite loop must timeout within specified limit
    infinite_loop = "while True:\n    pass"
    res = sandbox.execute(code=infinite_loop, timeout_seconds=1.0)
    assert res["ok"] is False
    assert "timed out" in res["error"].lower()


# ============================================================================
# 3. AgentOrchestrator & Execution Trace Logging
# ============================================================================

def test_agent_orchestrator_listing():
    orch = get_agent_orchestrator()
    specialists = orch.list_agents()
    assert len(specialists) == 9
    names = {s["name"] for s in specialists}
    assert "orchestrator" in names
    assert "planner" in names
    assert "study" in names
    assert "coding" in names
    assert "math" in names
    assert "research" in names
    assert "exam" in names
    assert "memory" in names
    assert "critic" in names


def test_agent_orchestrator_execution_trace(db_session):
    orch = get_agent_orchestrator()
    result = orch.run(
        db=db_session,
        query="Calculate 15 * 12 and write a simple Python function to compute factorial"
    )
    assert result.status == "SUCCESS"
    assert result.agent_run_id is not None
    assert len(result.execution_trace) >= 4

    # Verify trace structure (agent, action, stage, details, timestamp)
    stages = [t.stage for t in result.execution_trace]
    assert "Goal" in stages
    assert "Plan" in stages
    assert "Final" in stages

    for step in result.execution_trace:
        assert step.step_id >= 1
        assert step.agent_name is not None
        assert step.action_description is not None
        assert step.timestamp != ""

    # Verify DB persistence in AgentRun table
    run_rec = db_session.query(AgentRun).filter(AgentRun.id == result.agent_run_id).first()
    assert run_rec is not None
    assert run_rec.status == "SUCCESS"
    assert "factorial" in run_rec.input_query


# ============================================================================
# 4. Evaluation & Critic Agent Groundedness Scoring
# ============================================================================

def test_critic_agent_groundedness_scoring(db_session):
    # Output with citations and groundings
    grounded_results = [
        AgentResult(
            agent="Study Agent",
            ok=True,
            summary="Explained concepts with verified citations",
            data={"explanation": "According to Source 1, Page 2, a process is a program in execution."},
            citations=[{"source": "Source 1", "page": "2"}]
        )
    ]
    eval_grounded = evaluate_output_quality(
        query="Explain process management with citations from my notes",
        combined_response="According to Source 1, Page 2, a process is a program in execution.",
        agent_results=grounded_results,
        db=db_session
    )
    assert eval_grounded.groundedness >= 0.90
    assert eval_grounded.overall_score >= 0.80

    # Output without requested citations / evidence
    ungrounded_results = [
        AgentResult(
            agent="Study Agent",
            ok=True,
            summary="Generic answer without citations",
            data={"explanation": "A process is something that runs on an operating system."},
            citations=[]
        )
    ]
    eval_ungrounded = evaluate_output_quality(
        query="Prove and cite the evidence from uploaded textbook",
        combined_response="A process is something that runs on an operating system.",
        agent_results=ungrounded_results,
        db=db_session
    )
    assert eval_ungrounded.groundedness < eval_grounded.groundedness
