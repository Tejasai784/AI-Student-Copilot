"""Semantic Search Tool.
Performs vector similarity search across all indexed chunks in the local vector store.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from tools.registry import BaseTool
from rag.vector_store import get_vector_store
from rag.embeddings import get_embedding_generator


class SemanticSearchTool(BaseTool):
    name = "semantic_search"
    description = "Searches student's uploaded textbooks, notes, and syllabus using vector semantic retrieval."
    parameters_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Natural language query or topic to search for in uploaded materials."
            },
            "top_k": {
                "type": "integer",
                "description": "Number of top matching passages to return (default 4)."
            },
            "subject_id": {
                "type": "integer",
                "description": "Optional subject ID filter."
            }
        },
        "required": ["query"]
    }

    def execute(self, query: str, top_k: int = 4, subject_id: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        q = (query or "").strip()
        if not q:
            return {"ok": False, "error": "Search query cannot be empty."}

        v_store = get_vector_store()
        if v_store.count() == 0:
            return {
                "ok": True,
                "matches": [],
                "count": 0,
                "note": "No documents are currently indexed in the vector store."
            }

        embedder = get_embedding_generator()
        q_vec = embedder.embed_text(q)
        results = v_store.search(
            query_embedding=q_vec,
            top_k=top_k,
            filter_subject_id=subject_id
        )

        matches = []
        for r in results:
            matches.append({
                "score": r.get("score", 0.0),
                "document_id": r.get("document_id"),
                "page_number": r.get("page_number"),
                "unit_number": r.get("unit_number"),
                "content": r.get("content", "")
            })

        return {
            "ok": True,
            "query": q,
            "count": len(matches),
            "matches": matches
        }
