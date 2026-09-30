"""Study Agent — explains concepts, summarizes materials, creates notes, flashcards, and revision plans."""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from agents.contracts import AgentRequest, AgentResult, ToolExecutionStep
from backend.security import safe_user_error
from tools.registry import get_tool_registry
from services.llm_client import call_llm


def run_study_agent(request: AgentRequest, db: Optional[Session] = None, agent_run_id: Optional[int] = None) -> AgentResult:
    tool_steps: List[ToolExecutionStep] = []
    reg = get_tool_registry()

    try:
        query = request.query
        q_low = query.lower()

        # Step 1: Use semantic_search tool to check for uploaded notes
        retrieved_context = ""
        citations = []
        search_args = {"query": query, "top_k": 3}
        if request.subject_id:
            search_args["subject_id"] = request.subject_id
        
        search_out = reg.execute_tool("semantic_search", search_args, db=db, agent_run_id=agent_run_id)
        tool_steps.append(ToolExecutionStep(
            tool_name="semantic_search",
            arguments=search_args,
            output=search_out,
            execution_time_ms=search_out.get("execution_time_ms", 0.0),
            status="SUCCESS" if search_out.get("ok") else "FAILED"
        ))

        matches = search_out.get("matches", [])
        if matches:
            passages = []
            for m in matches:
                p_num = m.get("page_number", 1)
                doc_id = m.get("document_id", "N/A")
                passages.append(f"[Document #{doc_id}, Page {p_num}]: {m.get('content', '')}")
                citations.append({"document_id": str(doc_id), "page_number": str(p_num)})
            retrieved_context = "\n\n".join(passages)

        # Step 2: Generate educational synthesis via LLM with study agent system prompt
        sys_prompt = (
            "You are the specialist Study Agent in an autonomous student copilot platform. "
            "Your role is to explain academic concepts clearly, summarize material, "
            "create structured study notes, flashcards, and step-by-step revision checklists. "
            "Use clear headings, bullet points, and highlight high-yield exam takeaways."
        )

        prompt = f"Student query: {query}\n"
        if retrieved_context:
            prompt += f"\nRelevant passages from uploaded student course materials:\n{retrieved_context}\n"

        prompt += "\nPlease provide: 1. Core Concept Explanation, 2. Key Definitions & Rules, 3. 3 High-Yield Flashcards (Q & A), 4. Revision Checklist."

        text_response, model_label = call_llm(prompt=prompt, system_instruction=sys_prompt)

        return AgentResult(
            agent="Study Agent",
            ok=True,
            summary=f"Explained '{query[:60]}' with structured notes and flashcards ({model_label}).",
            data={
                "explanation": text_response,
                "retrieved_context_used": bool(retrieved_context),
                "model": model_label
            },
            tool_calls=tool_steps,
            citations=citations
        )
    except Exception as exc:
        return AgentResult(
            agent="Study Agent",
            ok=False,
            summary="Study agent encountered an error.",
            error=safe_user_error(exc)
        )
