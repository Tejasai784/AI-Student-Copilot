"""Student Memory Management Module.
Handles persistent learning context, user preferences, active goals, strengths,
weaknesses, and privacy safeguards (preventing sensitive data storage).
"""
from __future__ import annotations

import re
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session

from backend.logging_config import logger
from database.crud import (
    save_memory,
    get_memories,
    delete_memory
)
from database.models import Memory


SENSITIVE_PATTERNS = [
    re.compile(r"(password|secret|api[_-]?key|token|bearer|card\s*number|credit)", re.I),
    re.compile(r"sk-[A-Za-z0-9_\-]{8,}", re.I),
    re.compile(r"AIza[A-Za-z0-9_\-]{8,}", re.I),
    re.compile(r"\b\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}\b"),  # Credit card
    re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),  # Raw emails unless flagged
]


class MemoryManager:
    """Manages student memory operations with privacy checks and relevance ranking."""

    def __init__(self, db: Session):
        self.db = db

    def is_sensitive(self, text: str) -> bool:
        """Checks if text contains credentials, personal financial, or confidential keys."""
        for pattern in SENSITIVE_PATTERNS:
            if pattern.search(text):
                return True
        return False

    def store_fact(
        self,
        key: str,
        value: str,
        memory_type: str = "context",
        context: Optional[str] = None,
        importance: int = 3,
        user_id: Optional[int] = None
    ) -> Optional[Memory]:
        """Stores a memory item while filtering sensitive info."""
        if self.is_sensitive(value) or self.is_sensitive(key):
            logger.warning(f"Prevented storing sensitive content in student memory: {key}")
            return None

        return save_memory(
            db=self.db,
            key=key,
            value=value,
            memory_type=memory_type,
            context=context,
            importance=importance,
            is_sensitive=False,
            user_id=user_id
        )

    def record_weakness(self, topic_name: str, subject_name: str, notes: str = "") -> Memory:
        """Stores a detected academic weakness."""
        key = f"weakness_{subject_name.lower().replace(' ', '_')}_{topic_name.lower().replace(' ', '_')}"
        return self.store_fact(
            key=key,
            value=f"Struggles with {topic_name} in {subject_name}. {notes}".strip(),
            memory_type="weakness",
            importance=1
        )

    def record_mastery(self, topic_name: str, subject_name: str, score: float = 100.0) -> Memory:
        """Stores a detected academic strength / mastery."""
        key = f"mastery_{subject_name.lower().replace(' ', '_')}_{topic_name.lower().replace(' ', '_')}"
        return self.store_fact(
            key=key,
            value=f"Demonstrated mastery ({score}%) in {topic_name} ({subject_name}).",
            memory_type="strength",
            importance=2
        )

    def get_context_for_prompt(self, query: str, limit: int = 5) -> str:
        """Retrieves top relevant memory items to inject as context into agent prompts."""
        all_memories = get_memories(self.db, exclude_sensitive=True)
        if not all_memories:
            return ""

        q_terms = set(re.findall(r"\w+", query.lower()))
        scored = []
        for m in all_memories:
            score = 0
            m_text = f"{m.key} {m.value} {m.context or ''}".lower()
            for term in q_terms:
                if len(term) > 3 and term in m_text:
                    score += 2
            # Higher importance gives higher rank (1 is highest)
            score += (6 - m.importance)
            scored.append((score, m))

        scored.sort(key=lambda x: x[0], reverse=True)
        top = [item for _, item in scored[:limit]]

        lines = ["[Student Persistent Memory & Profile Context]:"]
        for m in top:
            lines.append(f"- ({m.memory_type.upper()}) {m.key}: {m.value}")
        return "\n".join(lines)

    def list_all_memories(self, memory_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns serializable dictionary list of memory records for the UI."""
        mems = get_memories(self.db, memory_type=memory_type)
        return [
            {
                "id": m.id,
                "key": m.key,
                "value": m.value,
                "memory_type": m.memory_type,
                "importance": m.importance,
                "context": m.context,
                "created_at": m.created_at.isoformat() if m.created_at else None
            }
            for m in mems
        ]

    def remove_memory(self, memory_id: int) -> bool:
        """Deletes a memory item by ID."""
        return delete_memory(self.db, memory_id)
