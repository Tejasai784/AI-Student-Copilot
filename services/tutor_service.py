"""
services/tutor_service.py — AI Tutor answer generation service.

Orchestrates:
  1. RAG retrieval (rag/retriever.py)
  2. Prompt construction (with or without retrieved context)
  3. LLM call (Gemini → OpenAI → offline fallback)
  4. TutorResponse assembly with honest source attribution
"""
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from backend.config import settings
from backend.logging_config import logger
from rag.retriever import retrieve_chunks, build_context_block, RetrievalResult


# ---------------------------------------------------------------------------
# Answer mode definitions
# ---------------------------------------------------------------------------

ANSWER_MODES: Dict[str, str] = {
    "Simple explanation": (
        "Give a clear, concise explanation in simple language. "
        "Avoid jargon. Aim for 3–5 sentences."
    ),
    "Detailed explanation": (
        "Give a thorough, multi-paragraph explanation covering all key concepts. "
        "Use structured prose with logical flow."
    ),
    "Exam answer": (
        "Write a formal, academic-style answer suitable for a university exam. "
        "Use correct terminology, structured paragraphs, and conclude clearly."
    ),
    "2-mark answer": (
        "Write a precise 2-mark exam answer. "
        "Keep it to 2–3 sentences covering only the core definition or fact."
    ),
    "5-mark answer": (
        "Write a 5-mark exam answer. "
        "Cover the main concept, key points, and a brief example. ~150 words."
    ),
    "10-mark answer": (
        "Write a comprehensive 10-mark exam answer. "
        "Include introduction, detailed explanation with sub-points, examples, "
        "and a conclusion. ~300–400 words."
    ),
    "With examples": (
        "Explain the concept clearly and include at least one concrete, "
        "worked example to illustrate the idea."
    ),
}

DEFAULT_ANSWER_MODE = "Simple explanation"


# ---------------------------------------------------------------------------
# Response dataclass
# ---------------------------------------------------------------------------

@dataclass
class TutorResponse:
    """
    Structured answer from the AI Tutor.

    source_mode values:
      "material"    — answer grounded in uploaded study material
      "general"     — no matching material; answer from model's general knowledge
      "no_material" — vector store empty / no material uploaded at all
      "offline"     — no LLM key configured; context shown as-is
    """
    answer: str = ""
    source_mode: str = "general"   # "material" | "general" | "no_material" | "offline"
    sources: List[Dict[str, Any]] = field(default_factory=list)
    model_used: str = "none"
    retrieval_score: float = 0.0
    answer_mode: str = DEFAULT_ANSWER_MODE
    query: str = ""
    error: Optional[str] = None


from models.ai_provider import get_ai_provider, GeminiProvider, OpenAIProvider, OfflineMockProvider
from services.llm_client import llm_available


# ---------------------------------------------------------------------------
# LLM client helpers
# ---------------------------------------------------------------------------

def _call_gemini(prompt: str, system_instruction: str) -> str:
    """Calls Gemini via google-genai SDK through GeminiProvider."""
    gemini = GeminiProvider()
    return gemini.generate_text(prompt, system_instruction=system_instruction)


def _call_openai(prompt: str, system_instruction: str) -> str:
    """Calls OpenAI chat completions API through OpenAIProvider."""
    openai_p = OpenAIProvider()
    return openai_p.generate_text(prompt, system_instruction=system_instruction)


def _call_llm(prompt: str, system_instruction: str) -> tuple[str, str]:
    """
    Calls the configured active AI provider via get_ai_provider().
    Returns (answer_text, model_label) or raises RuntimeError if unavailable or failed.
    """
    settings.reload()
    provider = get_ai_provider()
    if isinstance(provider, OfflineMockProvider) or not provider.is_available():
        raise RuntimeError("No AI service is configured.")
    try:
        text = provider.generate_text(prompt, system_instruction=system_instruction)
        return text, provider.get_model_name()
    except Exception as exc:
        logger.warning(f"AI provider generation failed: {exc}")
        raise RuntimeError(f"AI generation failed: {exc}") from exc


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

_BASE_SYSTEM = (
    "You are an AI Academic Tutor helping a university student understand their course material. "
    "Be accurate, educational, and honest. "
    "Never fabricate information. "
    "If you cite material, only cite what is explicitly provided in the context below."
)

def _build_grounded_prompt(query: str, context_block: str, mode_instruction: str) -> tuple[str, str]:
    """Builds a material-grounded prompt pair (system, user)."""
    system = (
        f"{_BASE_SYSTEM}\n\n"
        f"Answer style: {mode_instruction}\n\n"
        "IMPORTANT RULES:\n"
        "1. Base your answer primarily on the STUDY MATERIAL provided below.\n"
        "2. If the material covers the topic only partially, say so and supplement carefully.\n"
        "3. Do NOT fabricate citations or page numbers not present in the context.\n"
        "4. Structure your answer clearly."
    )
    user = (
        f"STUDY MATERIAL (retrieved from student's uploaded documents):\n"
        f"{'='*60}\n"
        f"{context_block}\n"
        f"{'='*60}\n\n"
        f"STUDENT QUESTION: {query}\n\n"
        f"Please answer the question based on the study material above."
    )
    return system, user


def _build_general_prompt(query: str, mode_instruction: str) -> tuple[str, str]:
    """Builds a general-knowledge prompt (no retrieved material)."""
    system = (
        f"{_BASE_SYSTEM}\n\n"
        f"Answer style: {mode_instruction}\n\n"
        "IMPORTANT: No relevant study material was found for this question. "
        "Answer from your general academic knowledge. "
        "Make it clear that this is a general explanation, not from the student's uploaded material."
    )
    user = f"STUDENT QUESTION: {query}"
    return system, user


# ---------------------------------------------------------------------------
# Citation builder
# ---------------------------------------------------------------------------

def _build_sources(chunks: List[Dict[str, Any]], db_docs: Optional[Dict[int, Any]] = None) -> List[Dict[str, Any]]:
    """
    Converts raw vector-store chunk dicts into clean citation dicts.
    db_docs: optional mapping of document_id -> Document ORM object for filename lookup.
    """
    sources = []
    seen_ids = set()
    for chunk in chunks:
        doc_id = chunk.get("document_id")
        chunk_idx = chunk.get("chunk_index", 0)
        uid = (doc_id, chunk_idx)
        if uid in seen_ids:
            continue
        seen_ids.add(uid)

        filename = "Unknown document"
        if db_docs and doc_id in db_docs:
            filename = db_docs[doc_id].filename

        sources.append({
            "document_id": doc_id,
            "filename": filename,
            "page_number": chunk.get("page_number", "?"),
            "subject_id": chunk.get("subject_id"),
            "unit_number": chunk.get("unit_number"),
            "topic_name": chunk.get("topic_name") or "General",
            "excerpt": chunk.get("content", "")[:300].strip(),
            "score": chunk.get("score", 0.0),
            "chunk_index": chunk_idx,
        })
    return sources


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_tutor_response(
    query: str,
    subject_id: Optional[int] = None,
    unit_number: Optional[int] = None,
    answer_mode: str = DEFAULT_ANSWER_MODE,
    top_k: int = settings.RAG_TOP_K,
    db_docs: Optional[Dict[int, Any]] = None,
    user_id: Optional[int] = None,
) -> TutorResponse:
    """
    Main entry point: retrieves relevant chunks then calls the LLM to generate an answer.

    Args:
        query: Student's natural-language question.
        subject_id: Optional subject filter for retrieval.
        unit_number: Optional unit filter for retrieval.
        answer_mode: One of the ANSWER_MODES keys.
        top_k: Number of chunks to retrieve.
        db_docs: Optional {document_id: Document} map for filename resolution in citations.
        user_id: Optional user scoping filter.

    Returns:
        TutorResponse with answer, source_mode, and source citations.
    """
    if not query or not query.strip():
        return TutorResponse(
            answer="Please enter a question.",
            source_mode="general",
            query=query,
        )

    mode_instruction = ANSWER_MODES.get(answer_mode, ANSWER_MODES[DEFAULT_ANSWER_MODE])

    # Reload environment to catch any recent changes to .env or environment variables
    settings.reload()

    # 1. Retrieve relevant chunks (user-scoped)
    retrieval: RetrievalResult = retrieve_chunks(
        query=query,
        top_k=top_k,
        subject_id=subject_id,
        unit_number=unit_number,
        user_id=user_id,
    )

    has_material = len(retrieval.chunks) > 0
    top_score = retrieval.chunks[0].get("score", 0.0) if has_material else 0.0

    # 2. Check if LLM is available via unified provider factory
    settings.reload()
    provider = get_ai_provider()
    has_llm = not isinstance(provider, OfflineMockProvider) and provider.is_available()

    # --- No material at all (vector store empty for this subject/filter) ---
    if not has_material:
        if not has_llm:
            return TutorResponse(
                answer=(
                    "No study material has been indexed for this query, "
                    "and no AI service is configured.\n\n"
                    "Please upload study materials and add `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) to your `.env` file to enable AI-generated answers."
                ),
                source_mode="no_material",
                sources=[],
                model_used="offline",
                query=query,
                answer_mode=answer_mode,
            )

        # General AI explanation — no fabricated citations
        system, user = _build_general_prompt(query, mode_instruction)
        try:
            answer_text, model_label = _call_llm(user, system)
            return TutorResponse(
                answer=answer_text,
                source_mode="no_material",
                sources=[],
                model_used=model_label,
                retrieval_score=0.0,
                query=query,
                answer_mode=answer_mode,
            )
        except RuntimeError as e:
            return TutorResponse(
                answer=f"Could not generate an answer: {e}",
                source_mode="no_material",
                sources=[],
                model_used="error",
                error=str(e),
                query=query,
                answer_mode=answer_mode,
            )

    # --- Material found ---
    context_block = build_context_block(retrieval.chunks)
    sources = _build_sources(retrieval.chunks, db_docs)

    if not has_llm:
        # Offline mode: return context as the "answer" with a clear disclaimer
        offline_answer = (
            "**Note: No AI service is configured. Showing retrieved study material directly.**\n\n"
            "Add `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) to your `.env` file to enable AI-generated answers.\n\n"
            "---\n\n"
        )
        for i, chunk in enumerate(retrieval.chunks, 1):
            page = chunk.get("page_number", "?")
            content = chunk.get("content", "").strip()
            offline_answer += f"**Source {i} (Page {page}):**\n{content}\n\n"
        return TutorResponse(
            answer=offline_answer,
            source_mode="offline",
            sources=sources,
            model_used="offline",
            retrieval_score=top_score,
            query=query,
            answer_mode=answer_mode,
        )

    # LLM call with grounded context
    system, user = _build_grounded_prompt(query, context_block, mode_instruction)
    try:
        answer_text, model_label = _call_llm(user, system)
        return TutorResponse(
            answer=answer_text,
            source_mode="material",
            sources=sources,
            model_used=model_label,
            retrieval_score=top_score,
            query=query,
            answer_mode=answer_mode,
        )
    except RuntimeError as e:
        logger.error(f"LLM call failed for grounded answer: {e}")
        # Fallback: return context text with error message
        fallback_answer = (
            f"**AI service error:** {e}\n\n"
            "Here is the relevant material retrieved from your study documents:\n\n"
            "---\n\n"
        )
        for i, chunk in enumerate(retrieval.chunks, 1):
            page = chunk.get("page_number", "?")
            content = chunk.get("content", "").strip()
            fallback_answer += f"**Source {i} (Page {page}):**\n{content}\n\n"
        return TutorResponse(
            answer=fallback_answer,
            source_mode="material",
            sources=sources,
            model_used="error",
            retrieval_score=top_score,
            error=str(e),
            query=query,
            answer_mode=answer_mode,
        )


ask_tutor = get_tutor_response
