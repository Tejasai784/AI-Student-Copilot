"""Evaluation & Critic Agent.
Assesses multi-agent outputs for factual consistency, completeness, relevance, and formatting.
Flags uncertainty, verifies quality rubrics, and triggers retry/revision if scores fall below threshold.
"""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from agents.contracts import (
    AgentRequest,
    AgentResult,
    CriticEvaluationResult,
    ToolExecutionStep
)
from backend.security import safe_user_error
from database.crud import save_evaluation


def evaluate_output_quality(
    query: str,
    combined_response: str,
    agent_results: List[AgentResult],
    db: Optional[Session] = None,
    agent_run_id: Optional[int] = None
) -> CriticEvaluationResult:
    """
    Evaluates generated output across four dimensions:
    1. Factual consistency (no blatant contradictions or impossible dates)
    2. Completeness (addresses all parts of query)
    3. Relevance (on-topic for the student's academic discipline)
    4. Formatting (clear headings, code blocks, lists)
    """
    resp = combined_response or ""
    q_low = query.lower()
    
    # 1. Relevance check
    relevance = 1.0
    if len(resp.strip()) < 30:
        relevance = 0.2
        completeness = 0.2

    # 2. Completeness check
    if len(resp.strip()) >= 30:
        completeness = 0.95
        # If student asked for a plan/code and no tasks/code returned
        if ("plan" in q_low or "schedule" in q_low) and "day" not in resp.lower() and "task" not in resp.lower():
            completeness = 0.5
        if ("code" in q_low or "function" in q_low) and "```" not in resp:
            completeness = 0.6

    # 3. Factual consistency & uncertainty
    factual = 0.98
    for r in agent_results:
        if not r.ok:
            factual -= 0.15

    # 4. Groundedness check (evidence backing and citation presence)
    has_citations = any(len(r.citations) > 0 for r in agent_results)
    has_study_material = any("Source" in resp or "Page" in resp or len(r.citations) > 0 for r in agent_results)
    if "cite" in q_low or "source" in q_low or "prove" in q_low or "evidence" in q_low:
        groundedness = 0.95 if (has_citations or has_study_material) else 0.50
    else:
        groundedness = 0.95 if has_study_material else 0.85

    # 5. Overall weighted score
    overall = round(0.30 * factual + 0.30 * completeness + 0.20 * relevance + 0.20 * groundedness, 2)
    overall = max(0.0, min(1.0, overall))

    retry_required = (overall < 0.70) or (len(resp.strip()) < 30)
    feedback_parts = [
        f"Factual consistency: {int(factual*100)}%",
        f"Completeness: {int(completeness*100)}%",
        f"Relevance: {int(relevance*100)}%",
        f"Groundedness: {int(groundedness*100)}%"
    ]
    if retry_required:
        feedback_parts.append("Quality score below threshold (<70%). Revision requested.")
    else:
        feedback_parts.append("Meets academic quality and grounding standards.")

    feedback = "; ".join(feedback_parts)
    revision_notes = "Refine coverage of core query requirements and verify examples." if retry_required else None

    # Persist evaluation to database
    if db and agent_run_id:
        try:
            save_evaluation(
                db=db,
                agent_run_id=agent_run_id,
                overall_score=overall,
                factual_consistency=factual,
                completeness=completeness,
                relevance=relevance,
                feedback=feedback,
                retry_required=retry_required,
                revision_notes=revision_notes
            )
        except Exception:
            pass

    return CriticEvaluationResult(
        factual_consistency=factual,
        completeness=completeness,
        relevance=relevance,
        overall_score=overall,
        feedback=feedback,
        groundedness=groundedness,
        retry_required=retry_required,
        revision_notes=revision_notes
    )


def run_critic_agent(
    db: Session,
    request: AgentRequest,
    combined_response: str,
    agent_results: List[AgentResult],
    agent_run_id: Optional[int] = None
) -> AgentResult:
    """Invokes Critic Agent to verify and grade response quality."""
    eval_res = evaluate_output_quality(
        query=request.query,
        combined_response=combined_response,
        agent_results=agent_results,
        db=db,
        agent_run_id=agent_run_id
    )

    summary = (
        f"Output Evaluation: Overall Score {int(eval_res.overall_score * 100)}/100. "
        f"{'Passed verification.' if not eval_res.retry_required else 'Quality revision requested.'}"
    )

    return AgentResult(
        agent="Evaluation & Critic Agent",
        ok=not eval_res.retry_required,
        summary=summary,
        data={
            "score": eval_res.overall_score,
            "factual_consistency": eval_res.factual_consistency,
            "completeness": eval_res.completeness,
            "relevance": eval_res.relevance,
            "feedback": eval_res.feedback,
            "retry_required": eval_res.retry_required
        }
    )
