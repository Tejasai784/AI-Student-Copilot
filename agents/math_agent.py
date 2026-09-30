"""Mathematics Agent — solves math problems step-by-step and verifies calculations using calculator tool."""
from __future__ import annotations

import re
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from agents.contracts import AgentRequest, AgentResult, ToolExecutionStep
from backend.security import safe_user_error
from tools.registry import get_tool_registry
from services.llm_client import call_llm


def run_math_agent(request: AgentRequest, db: Optional[Session] = None, agent_run_id: Optional[int] = None) -> AgentResult:
    tool_steps: List[ToolExecutionStep] = []
    reg = get_tool_registry()

    try:
        query = request.query

        # Check if an arithmetic/math calculation can be verified via calculator tool
        calc_out = None
        # Look for patterns like "15 * 4" or "sqrt(144)" or "2**10"
        math_expr_match = re.search(r"(\(?\d+[\s\+\-\*\/\%\^]+\d+[\s\+\-\*\/\%\^\d\(\)]*|\bsqrt\(\d+\)|\bsin\([0-9\.]+\))", query)
        if math_expr_match:
            expr = math_expr_match.group(1).replace("^", "**")
            tool_args = {"expression": expr}
            calc_out = reg.execute_tool("calculator", tool_args, db=db, agent_run_id=agent_run_id)
            tool_steps.append(ToolExecutionStep(
                tool_name="calculator",
                arguments=tool_args,
                output=calc_out,
                execution_time_ms=calc_out.get("execution_time_ms", 0.0),
                status="SUCCESS" if calc_out.get("ok") else "FAILED"
            ))

        sys_prompt = (
            "You are the specialist Mathematics Agent in an autonomous student copilot platform. "
            "Your role is to solve mathematical problems step-by-step with rigorous derivations, "
            "clear explanations of principles and theorems, and explicit calculation checks. "
            "Use LaTeX formatting for formulas (inline $...$ and display $$...$$)."
        )

        prompt = f"Student math problem: {query}\n"
        if calc_out and calc_out.get("ok"):
            prompt += f"\nVerified calculator tool result:\n{calc_out['expression']} = {calc_out['formatted_result']}\n"

        prompt += "\nPlease show: 1. Problem Statement, 2. Formulas/Principles Used, 3. Step-by-Step Derivation, 4. Final Answer & Sanity Check."

        math_explanation, model_label = call_llm(prompt=prompt, system_instruction=sys_prompt)

        return AgentResult(
            agent="Mathematics Agent",
            ok=True,
            summary=f"Solved math problem step-by-step with calculation verification ({model_label}).",
            data={
                "solution": math_explanation,
                "calculator_used": bool(calc_out and calc_out.get("ok")),
                "calc_result": calc_out
            },
            tool_calls=tool_steps
        )
    except Exception as exc:
        return AgentResult(
            agent="Mathematics Agent",
            ok=False,
            summary="Mathematics agent encountered an error.",
            error=safe_user_error(exc)
        )
