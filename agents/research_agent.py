"""Research Agent — retrieves facts from permitted sources, distinguishes facts from reasoning, and records citations."""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from agents.contracts import AgentRequest, AgentResult, ToolExecutionStep
from backend.security import safe_user_error
from tools.registry import get_tool_registry
from services.llm_client import call_llm


def run_research_agent(request: AgentRequest, db: Optional[Session] = None, agent_run_id: Optional[int] = None) -> AgentResult:
    tool_steps: List[ToolExecutionStep] = []
    citations: List[Dict[str, str]] = []
    reg = get_tool_registry()

    try:
        query = request.query

        # Step 1: Use web_research tool
        tool_args = {"query": query}
        web_out = reg.execute_tool("web_research", tool_args, db=db, agent_run_id=agent_run_id)
        tool_steps.append(ToolExecutionStep(
            tool_name="web_research",
            arguments=tool_args,
            output=web_out,
            execution_time_ms=web_out.get("execution_time_ms", 0.0),
            status="SUCCESS" if web_out.get("ok") else "FAILED"
        ))

        retrieved_facts = web_out.get("retrieved_facts", [])
        for f in retrieved_facts:
            citations.append({"url": f.get("source", ""), "domain": f.get("domain", "")})

        # Step 2: Use semantic_search tool for course notes grounding
        search_args = {"query": query, "top_k": 2}
        s_out = reg.execute_tool("semantic_search", search_args, db=db, agent_run_id=agent_run_id)
        tool_steps.append(ToolExecutionStep(
            tool_name="semantic_search",
            arguments=search_args,
            output=s_out,
            execution_time_ms=s_out.get("execution_time_ms", 0.0),
            status="SUCCESS" if s_out.get("ok") else "FAILED"
        ))

        matches = s_out.get("matches", [])
        for m in matches:
            citations.append({"document_id": str(m.get("document_id")), "page_number": str(m.get("page_number"))})

        sys_prompt = (
            "You are the specialist Research Agent in an autonomous student copilot platform. "
            "Your objective is to provide rigorously cited, factual information. "
            "You MUST clearly distinguish between verified retrieved facts and your own synthetic reasoning. "
            "Format the response into two explicit sections: "
            "1. Verified Factual Findings (with inline source URLs and page citations), and "
            "2. Conceptual Synthesis & Academic Implications."
        )

        facts_text = "\n".join(f"- [{item.get('domain', 'source')}]: {item.get('fact', '')}" for item in retrieved_facts)
        notes_text = "\n".join(f"- [Course Doc #{m.get('document_id')} P.{m.get('page_number')}]: {m.get('content')}" for m in matches)

        prompt = (
            f"Research Query: {query}\n\n"
            f"Verified External Facts:\n{facts_text}\n\n"
            f"Indexed Course Notes:\n{notes_text}\n\n"
            "Please deliver a complete, cited academic research summary."
        )

        research_text, model_label = call_llm(prompt=prompt, system_instruction=sys_prompt)

        return AgentResult(
            agent="Research Agent",
            ok=True,
            summary=f"Synthesized research from {len(citations)} academic sources ({model_label}).",
            data={
                "research_summary": research_text,
                "sources_count": len(citations),
                "citations": citations
            },
            tool_calls=tool_steps,
            citations=citations
        )
    except Exception as exc:
        return AgentResult(
            agent="Research Agent",
            ok=False,
            summary="Research agent encountered an error.",
            error=safe_user_error(exc)
        )
