"""Memory Agent — manages student long-term context, retrieval of prior performance, and privacy safeguards."""
from __future__ import annotations

from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session

from agents.contracts import AgentRequest, AgentResult, ToolExecutionStep
from backend.security import safe_user_error
from memory.memory_manager import MemoryManager


def run_memory_agent(db: Session, request: AgentRequest, agent_run_id: Optional[int] = None) -> AgentResult:
    try:
        mem_mgr = MemoryManager(db)
        query = request.query

        # Retrieve relevant prior context
        context_str = mem_mgr.get_context_for_prompt(query, limit=5)
        all_memories = mem_mgr.list_all_memories()

        # Check if query requests storing a preference or fact
        stored_item = None
        if "i prefer" in query.lower() or "my exam date is" in query.lower() or "remember that" in query.lower():
            key = f"user_fact_{len(all_memories) + 1}"
            stored_item = mem_mgr.store_fact(
                key=key,
                value=query,
                memory_type="preference",
                importance=2,
                user_id=request.user_id
            )

        summary = (
            f"Retrieved {len(all_memories)} student memory records. "
            f"{'Recorded new persistent context.' if stored_item else 'Context injected for active session.'}"
        )

        return AgentResult(
            agent="Memory Agent",
            ok=True,
            summary=summary,
            data={
                "memory_context": context_str,
                "total_memories": len(all_memories),
                "new_memory_stored": bool(stored_item)
            }
        )
    except Exception as exc:
        return AgentResult(
            agent="Memory Agent",
            ok=False,
            summary="Memory agent encountered an error.",
            error=safe_user_error(exc)
        )
