"""Analysis Agent — performance and weak-topic evidence."""
from __future__ import annotations

from sqlalchemy.orm import Session

from agents.contracts import AgentRequest, AgentResult
from backend.security import safe_user_error
from services.analytics_service import compute_performance, detect_weak_topics, strong_topics


def run_analysis_agent(db: Session, request: AgentRequest) -> AgentResult:
    try:
        stats = compute_performance(db)
        weak = detect_weak_topics(db)
        if request.subject_id:
            weak = [w for w in weak if w.get("subject_id") in {request.subject_id, 0}]
            stats = {**stats, "topic_mastery": [t for t in stats["topic_mastery"] if t.get("subject_id") in {request.subject_id, 0}]}
        summary = (
            f"Overall accuracy {stats.get('overall_accuracy')}% across {stats.get('total_attempts')} attempts. "
            f"Weak topics (evidence-based): {len(weak)}."
        )
        return AgentResult(
            agent="analysis",
            ok=True,
            summary=summary,
            data={"performance": stats, "weak_topics": weak, "strong_topics": strong_topics(db)},
        )
    except Exception as exc:
        return AgentResult(agent="analysis", ok=False, summary="Analysis agent failed.", error=safe_user_error(exc))
