"""
rag/retriever.py — RAG retrieval layer for the AI Tutor.

Wraps the LocalVectorStore search behind a clean, testable interface.
Handles query embedding, subject/unit filtering, and context-char capping.
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from backend.config import settings
from backend.logging_config import logger
from rag.embeddings import get_embedding_generator
from rag.vector_store import get_vector_store


@dataclass
class RetrievalResult:
    """
    Output of a single retrieval call.

    Attributes:
        chunks: Ranked list of matching vector-store metadata dicts (with 'score').
        query_embedding: The raw query embedding vector used for search.
        total_chars: Total character count across all returned chunks.
        truncated: True if some chunks were dropped due to max_context_chars.
        subject_id: Filter used (or None).
        unit_number: Filter used (or None).
    """
    chunks: List[Dict[str, Any]] = field(default_factory=list)
    query_embedding: List[float] = field(default_factory=list)
    total_chars: int = 0
    truncated: bool = False
    subject_id: Optional[int] = None
    unit_number: Optional[int] = None


def retrieve_chunks(
    query: str,
    top_k: int = settings.RAG_TOP_K,
    subject_id: Optional[int] = None,
    unit_number: Optional[int] = None,
    max_context_chars: int = settings.MAX_CONTEXT_CHARS,
) -> RetrievalResult:
    """
    Retrieve the most relevant chunks for a natural-language query.

    Steps:
    1. Embed the query using the configured embedding generator.
    2. Search the vector store with optional subject/unit filters.
    3. Trim results to stay within max_context_chars.
    4. Return a RetrievalResult with ranked chunks and metadata.

    Args:
        query: Student's natural-language question.
        top_k: Maximum number of chunks to retrieve.
        subject_id: If set, restrict search to this subject.
        unit_number: If set, further restrict to this unit (requires subject_id).
        max_context_chars: Hard cap on total context characters sent to the LLM.

    Returns:
        RetrievalResult with ranked chunks (may be empty if no material indexed).
    """
    if not query or not query.strip():
        logger.warning("retrieve_chunks called with empty query.")
        return RetrievalResult(subject_id=subject_id, unit_number=unit_number)

    # 1. Embed query
    embedder = get_embedding_generator()
    query_embedding = embedder.embed_text(query.strip())
    logger.debug(f"Query embedded: dim={len(query_embedding)}, query='{query[:60]}...'")

    # 2. Search vector store
    v_store = get_vector_store()
    raw_results = v_store.search(
        query_embedding=query_embedding,
        top_k=top_k,
        filter_subject_id=subject_id,
        filter_unit=unit_number,
    )
    logger.info(
        f"Vector search returned {len(raw_results)} results "
        f"(subject_id={subject_id}, unit={unit_number}, top_k={top_k})"
    )

    if not raw_results:
        return RetrievalResult(
            query_embedding=query_embedding,
            subject_id=subject_id,
            unit_number=unit_number,
        )

    # 3. Cap total context to max_context_chars
    included_chunks: List[Dict[str, Any]] = []
    running_chars = 0
    truncated = False

    for chunk in raw_results:
        chunk_len = len(chunk.get("content", ""))
        if running_chars + chunk_len > max_context_chars:
            truncated = True
            # Include partial chunk if it fits a minimum useful size (>= 100 chars)
            remaining = max_context_chars - running_chars
            if remaining >= 100:
                partial = dict(chunk)
                partial["content"] = chunk["content"][:remaining].rstrip()
                partial["char_count"] = len(partial["content"])
                included_chunks.append(partial)
                running_chars += len(partial["content"])
            break
        included_chunks.append(chunk)
        running_chars += chunk_len

    return RetrievalResult(
        chunks=included_chunks,
        query_embedding=query_embedding,
        total_chars=running_chars,
        truncated=truncated,
        subject_id=subject_id,
        unit_number=unit_number,
    )


def build_context_block(chunks: List[Dict[str, Any]]) -> str:
    """
    Formats retrieved chunks into a readable context string for the LLM prompt.

    Each chunk is numbered, labelled with its source document and page number.
    """
    if not chunks:
        return ""

    lines = []
    for i, chunk in enumerate(chunks, start=1):
        doc_id = chunk.get("document_id", "?")
        page = chunk.get("page_number", "?")
        topic = chunk.get("topic_name") or "General"
        content = chunk.get("content", "").strip()
        lines.append(
            f"[Source {i} | Document ID: {doc_id} | Page {page} | Topic: {topic}]\n{content}"
        )

    return "\n\n---\n\n".join(lines)
