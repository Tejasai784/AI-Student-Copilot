"""Generate practice/exam questions from RAG material or syllabus topics."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from backend.logging_config import logger
from rag.retriever import retrieve_chunks
from services.llm_client import call_llm, llm_available

QUESTION_TYPES = ["MCQ", "MULTI_SELECT", "TRUE_FALSE", "SHORT", "LONG", "CODE"]

DEFAULT_MARKS = {
    "MCQ": 1.0,
    "MULTI_SELECT": 2.0,
    "TRUE_FALSE": 1.0,
    "SHORT": 2.0,
    "LONG": 5.0,
    "CODE": 5.0,
}

LONG_MARK_OPTIONS = {2.0, 5.0, 10.0}


def _sentences(text: str) -> List[str]:
    parts = re.split(r"(?<=[.!?])\s+", (text or "").strip())
    return [p.strip() for p in parts if len(p.strip()) > 20]


def _keywords(text: str, limit: int = 8) -> List[str]:
    words = re.findall(r"\b[A-Za-z][A-Za-z0-9_-]{3,}\b", text or "")
    stop = {
        "this", "that", "with", "from", "which", "have", "been", "were", "they",
        "their", "about", "into", "also", "such", "than", "then", "when", "what",
        "your", "will", "each", "only", "more", "most", "some", "other",
    }
    uniq = []
    for w in words:
        lw = w.lower()
        if lw in stop or lw in uniq:
            continue
        uniq.append(lw)
        if len(uniq) >= limit:
            break
    return uniq


def _parse_json_list(raw: str) -> List[Dict[str, Any]]:
    if not raw:
        return []
    text = raw.strip()
    match = re.search(r"\[.*\]", text, re.DOTALL)
    if match:
        text = match.group(0)
    try:
        data = json.loads(text)
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def _normalize_question(raw: Dict[str, Any], fallback_type: str, difficulty: str, chunk: Optional[Dict] = None) -> Optional[Dict[str, Any]]:
    qtype = (raw.get("question_type") or fallback_type or "SHORT").upper().replace(" ", "_")
    if qtype in {"MULTIPLE_CHOICE", "MULTIPLE-CHOICE", "MCQS"}:
        qtype = "MCQ"
    if qtype not in QUESTION_TYPES:
        qtype = fallback_type if fallback_type in QUESTION_TYPES else "SHORT"
    text = (raw.get("question_text") or raw.get("question") or "").strip()
    if not text:
        return None
    options = raw.get("options") or []
    if isinstance(options, str):
        options = [o.strip() for o in options.split("\n") if o.strip()]
    marks = float(raw.get("max_marks") or DEFAULT_MARKS.get(qtype, 1))
    if qtype == "LONG" and marks not in LONG_MARK_OPTIONS:
        marks = 5.0
    item = {
        "question_type": qtype,
        "question_text": text,
        "options": options,
        "correct_answer": raw.get("correct_answer") or raw.get("answer") or "",
        "max_marks": marks,
        "difficulty": (raw.get("difficulty") or difficulty).lower(),
        "topic_name": raw.get("topic_name"),
        "explanation": raw.get("explanation") or "",
        "unit_number": (chunk or {}).get("unit_number"),
        "subject_id": (chunk or {}).get("subject_id"),
        "source_excerpt": (chunk or {}).get("content", "")[:400] if chunk else raw.get("source_excerpt"),
        "page_number": (chunk or {}).get("page_number"),
        "document_id": (chunk or {}).get("document_id"),
    }
    return item


def _heuristic_from_chunk(chunk: Dict[str, Any], qtype: str, difficulty: str, index: int) -> Dict[str, Any]:
    content = chunk.get("content") or ""
    sentences = _sentences(content)
    seed = sentences[index % len(sentences)] if sentences else content[:180]
    keys = _keywords(content)
    topic = chunk.get("topic_name") or (keys[0].title() if keys else "General")
    key = keys[0] if keys else "the topic"

    if qtype == "TRUE_FALSE":
        return _normalize_question(
            {
                "question_type": "TRUE_FALSE",
                "question_text": f"True or False: {seed}",
                "correct_answer": "True",
                "max_marks": 1,
                "explanation": "The statement is taken from the study material.",
                "topic_name": topic,
            },
            qtype,
            difficulty,
            chunk,
        )
    if qtype == "MCQ":
        distractors = [
            f"{key} is unrelated to this subject.",
            f"{key} can be ignored in examinations.",
            f"{key} is only a historical footnote.",
        ]
        correct = seed if seed else f"{key} is an important concept in this unit."
        options = [correct, *distractors][:4]
        return _normalize_question(
            {
                "question_type": "MCQ",
                "question_text": f"According to the study material, which statement about {key} is most accurate?",
                "options": options,
                "correct_answer": options[0],
                "max_marks": 1,
                "topic_name": topic,
            },
            qtype,
            difficulty,
            chunk,
        )
    if qtype == "MULTI_SELECT":
        opts = [
            f"{k} is relevant to this topic." for k in (keys[:3] or ["concept", "definition", "example"])
        ]
        opts.append("This topic has no academic importance.")
        return _normalize_question(
            {
                "question_type": "MULTI_SELECT",
                "question_text": f"Select all statements that apply to {topic}.",
                "options": opts,
                "correct_answer": opts[:-1],
                "max_marks": 2,
                "topic_name": topic,
            },
            qtype,
            difficulty,
            chunk,
        )
    if qtype == "LONG":
        marks = 10.0 if difficulty == "hard" else 5.0
        return _normalize_question(
            {
                "question_type": "LONG",
                "question_text": f"Explain {topic} in detail, covering key ideas from the material.",
                "correct_answer": seed,
                "max_marks": marks,
                "topic_name": topic,
            },
            qtype,
            difficulty,
            chunk,
        )
    if qtype == "CODE":
        return _normalize_question(
            {
                "question_type": "CODE",
                "question_text": (
                    f"Write a short function or pseudocode related to {topic}. "
                    f"Use the material's terminology. Hint: {seed[:120]}"
                ),
                "correct_answer": f"# Outline a solution involving {key}\npass",
                "max_marks": 5,
                "topic_name": topic,
            },
            qtype,
            difficulty,
            chunk,
        )
    # SHORT / 2-mark
    return _normalize_question(
        {
            "question_type": "SHORT",
            "question_text": f"Briefly define or state the key idea of {key} (2 marks).",
            "correct_answer": seed,
            "max_marks": 2,
            "topic_name": topic,
        },
        qtype,
        difficulty,
        chunk,
    )


def _heuristic_general(qtype: str, difficulty: str, topic: str, index: int) -> Dict[str, Any]:
    topic = topic or "this subject"
    stubs = [
        f"What is {topic}?",
        f"List two important properties of {topic}.",
        f"Why is {topic} important in examinations?",
        f"Give one example related to {topic}.",
    ]
    text = stubs[index % len(stubs)]
    dummy_chunk = {"content": topic, "topic_name": topic}
    return _heuristic_from_chunk(
        {
            "content": f"{topic} is a core academic topic. Students should understand definitions, properties, and applications of {topic}.",
            "topic_name": topic,
        },
        qtype,
        difficulty,
        index,
    )


def _llm_questions(
    context: str,
    types: List[str],
    count: int,
    difficulty: str,
    topic_name: Optional[str],
) -> List[Dict[str, Any]]:
    system = (
        "You generate university exam questions. "
        "Return ONLY a JSON array. No markdown. "
        "Each item: question_type, question_text, options (array), correct_answer, "
        "max_marks, difficulty, topic_name, explanation. "
        "Ground questions in the provided study material. Do not invent citations."
    )
    user = (
        f"Difficulty: {difficulty}\n"
        f"Topic: {topic_name or 'from material'}\n"
        f"Requested types (cycle as needed): {', '.join(types)}\n"
        f"Number of questions: {count}\n"
        f"Use SHORT=2 marks, LONG=5 or 10 marks, MCQ/TRUE_FALSE=1, CODE=5, MULTI_SELECT=2.\n\n"
        f"STUDY MATERIAL:\n{context[:5500]}"
    )
    text, _model = call_llm(user, system)
    parsed = _parse_json_list(text)
    results = []
    for item in parsed:
        q = _normalize_question(item, types[0], difficulty, None)
        if q:
            results.append(q)
    return results


def generate_questions(
    *,
    count: int = 5,
    question_types: Optional[List[str]] = None,
    difficulty: str = "medium",
    subject_id: Optional[int] = None,
    unit_number: Optional[int] = None,
    topic_name: Optional[str] = None,
    long_marks: float = 5.0,
) -> Dict[str, Any]:
    """
    Returns {questions, grounded, sources}.
    Prefers RAG-grounded generation; falls back to syllabus/heuristic.
    """
    types = [t.upper().replace(" ", "_") for t in (question_types or ["MCQ", "SHORT", "TRUE_FALSE"])]
    types = [t if t in QUESTION_TYPES else "SHORT" for t in types] or ["SHORT"]
    count = max(1, min(int(count), 20))
    difficulty = (difficulty or "medium").lower()

    query = topic_name or "important definitions concepts and exam topics"
    retrieval = retrieve_chunks(query=query, subject_id=subject_id, unit_number=unit_number)
    chunks = retrieval.chunks or []
    grounded = bool(chunks)

    questions: List[Dict[str, Any]] = []
    if grounded and llm_available():
        try:
            from rag.retriever import build_context_block

            questions = _llm_questions(build_context_block(chunks), types, count, difficulty, topic_name)
        except Exception as exc:
            logger.warning(f"LLM question generation failed, using heuristic: {type(exc).__name__}")
            questions = []

    if not questions:
        for i in range(count):
            qtype = types[i % len(types)]
            if chunks:
                questions.append(_heuristic_from_chunk(chunks[i % len(chunks)], qtype, difficulty, i))
            else:
                questions.append(_heuristic_general(qtype, difficulty, topic_name or "the selected subject", i))

    questions = [q for q in questions if q][:count]
    for q in questions:
        if q["question_type"] == "LONG":
            q["max_marks"] = float(long_marks if long_marks in LONG_MARK_OPTIONS else 5.0)
        if topic_name and not q.get("topic_name"):
            q["topic_name"] = topic_name
        if subject_id and not q.get("subject_id"):
            q["subject_id"] = subject_id
        if unit_number is not None and q.get("unit_number") is None:
            q["unit_number"] = unit_number

    sources = []
    for ch in chunks[:5]:
        sources.append(
            {
                "document_id": ch.get("document_id"),
                "page_number": ch.get("page_number"),
                "topic_name": ch.get("topic_name"),
                "excerpt": (ch.get("content") or "")[:200],
            }
        )
    return {"questions": questions, "grounded": grounded, "sources": sources}
