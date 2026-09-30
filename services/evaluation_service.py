"""Objective and AI-assisted subjective evaluation."""
from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional, Tuple

from backend.logging_config import logger
from database.academic_crud import _loads
from services.llm_client import call_llm, llm_available

OBJECTIVE_TYPES = {"MCQ", "MULTI_SELECT", "TRUE_FALSE"}
SUBJECTIVE_TYPES = {"SHORT", "LONG", "CODE"}

_TRUE = {"true", "t", "yes", "y", "1"}
_FALSE = {"false", "f", "no", "n", "0"}


def _norm(text: Optional[str]) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _split_multi(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [_norm(str(v)) for v in value if str(v).strip()]
    text = str(value)
    try:
        parsed = json.loads(text)
        if isinstance(parsed, list):
            return [_norm(str(v)) for v in parsed]
    except json.JSONDecodeError:
        pass
    return [_norm(p) for p in re.split(r"[,\n;]+", text) if p.strip()]


def _mcq_match(user: str, correct: str, options: Optional[List[str]]) -> bool:
    u, c = _norm(user), _norm(correct)
    if not u:
        return False
    if u == c:
        return True
    # Option letter: A / B / C
    if len(u) == 1 and u.isalpha() and options:
        idx = ord(u) - ord("a")
        if 0 <= idx < len(options) and _norm(options[idx]) == c:
            return True
        if 0 <= idx < len(options) and _norm(user) == _norm(options[idx][:1]):
            return _norm(options[idx]) == c
    if options:
        for opt in options:
            if u == _norm(opt) and _norm(opt) == c:
                return True
    return False


def grade_objective(question: Any, user_answer: str) -> Dict[str, Any]:
    qtype = question.question_type
    options = _loads(question.options_json, []) or []
    correct = question.correct_answer or ""
    max_marks = float(question.max_marks or 1)

    if qtype == "TRUE_FALSE":
        u = _norm(user_answer)
        c = _norm(correct)
        u_bool = True if u in _TRUE else False if u in _FALSE else None
        c_bool = True if c in _TRUE else False if c in _FALSE else c
        is_correct = False
        if u_bool is not None:
            if isinstance(c_bool, bool):
                is_correct = u_bool == c_bool
            else:
                is_correct = (u in _TRUE and c in _TRUE) or (u in _FALSE and c in _FALSE)
        score = max_marks if is_correct else 0.0
        return {
            "score": score,
            "max_marks": max_marks,
            "is_correct": is_correct,
            "grading_mode": "OBJECTIVE",
            "explanation": "Graded by exact True/False comparison (case-insensitive).",
            "model_answer": str(correct),
            "key_concepts": [],
            "missing_concepts": [] if is_correct else ["Correct true/false value"],
            "incorrect_concepts": [],
            "improvement_suggestions": "" if is_correct else "Review the related section in your notes and retry.",
        }

    if qtype == "MULTI_SELECT":
        user_set = set(_split_multi(user_answer))
        correct_set = set(_split_multi(correct))
        if not correct_set:
            correct_set = set(_norm(o) for o in options[:-1]) if options else set()
        is_correct = user_set == correct_set and bool(user_set)
        # Partial credit
        if correct_set:
            overlap = len(user_set & correct_set) / len(correct_set)
            extra = len(user_set - correct_set)
            score = max(0.0, round(max_marks * overlap - 0.25 * extra * max_marks, 2))
            if is_correct:
                score = max_marks
        else:
            score = 0.0
        return {
            "score": min(score, max_marks),
            "max_marks": max_marks,
            "is_correct": is_correct,
            "grading_mode": "OBJECTIVE",
            "explanation": "Graded by matching selected options (order-independent).",
            "model_answer": ", ".join(sorted(correct_set)),
            "key_concepts": sorted(correct_set),
            "missing_concepts": sorted(correct_set - user_set),
            "incorrect_concepts": sorted(user_set - correct_set),
            "improvement_suggestions": "" if is_correct else "Select only the options supported by the material.",
        }

    # MCQ
    is_correct = _mcq_match(user_answer, correct, options)
    return {
        "score": max_marks if is_correct else 0.0,
        "max_marks": max_marks,
        "is_correct": is_correct,
        "grading_mode": "OBJECTIVE",
        "explanation": "Graded by objective option comparison (case-insensitive).",
        "model_answer": str(correct),
        "key_concepts": [],
        "missing_concepts": [] if is_correct else ["Correct option"],
        "incorrect_concepts": [],
        "improvement_suggestions": "" if is_correct else "Re-read the source excerpt and eliminate distractors.",
    }


def _keyword_subjective(question: Any, user_answer: str) -> Dict[str, Any]:
    max_marks = float(question.max_marks or 2)
    model = question.correct_answer or question.explanation or question.source_excerpt or ""
    user = user_answer or ""
    keys = []
    for token in re.findall(r"\b[A-Za-z][A-Za-z0-9_-]{3,}\b", model.lower()):
        if token not in keys:
            keys.append(token)
        if len(keys) >= 8:
            break
    if not keys:
        keys = ["definition", "example"]
    present = [k for k in keys if k in user.lower()]
    missing = [k for k in keys if k not in present]
    ratio = len(present) / max(len(keys), 1)
    score = round(max_marks * ratio, 2)
    is_correct = ratio >= 0.7
    return {
        "score": score,
        "max_marks": max_marks,
        "is_correct": is_correct,
        "grading_mode": "AI_SUBJECTIVE",
        "explanation": (
            "Heuristic keyword overlap was used because no AI service is configured. "
            "This is an approximate score, not a human examiner mark."
        ),
        "model_answer": model[:800],
        "key_concepts": present,
        "missing_concepts": missing,
        "incorrect_concepts": [],
        "improvement_suggestions": (
            "Add the missing concepts and write in full sentences with an example."
            if missing
            else "Good coverage of the expected keywords."
        ),
    }


def _llm_subjective(question: Any, user_answer: str) -> Dict[str, Any]:
    max_marks = float(question.max_marks or 2)
    system = (
        "You are an academic examiner. Evaluate the student's answer. "
        "Return ONLY JSON with keys: score, max_marks, key_concepts, missing_concepts, "
        "incorrect_concepts, explanation, model_answer, improvement_suggestions. "
        "score must be <= max_marks. Be fair. Do not claim absolute certainty."
    )
    user = (
        f"Question type: {question.question_type}\n"
        f"Max marks: {max_marks}\n"
        f"Question: {question.question_text}\n"
        f"Reference / expected points: {question.correct_answer or question.source_excerpt or ''}\n"
        f"Student answer:\n{user_answer or '(blank)'}"
    )
    raw, _model = call_llm(user, system)
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    data = {}
    if match:
        try:
            data = json.loads(match.group(0))
        except json.JSONDecodeError:
            data = {}
    score = float(data.get("score", 0))
    score = max(0.0, min(score, max_marks))
    return {
        "score": round(score, 2),
        "max_marks": max_marks,
        "is_correct": score >= 0.7 * max_marks,
        "grading_mode": "AI_SUBJECTIVE",
        "explanation": data.get("explanation")
        or "AI-assisted subjective evaluation. Treat the mark as guidance, not official grading.",
        "model_answer": data.get("model_answer") or (question.correct_answer or ""),
        "key_concepts": data.get("key_concepts") or [],
        "missing_concepts": data.get("missing_concepts") or [],
        "incorrect_concepts": data.get("incorrect_concepts") or [],
        "improvement_suggestions": data.get("improvement_suggestions") or "",
    }


def grade_subjective(question: Any, user_answer: str) -> Dict[str, Any]:
    if not (user_answer or "").strip():
        max_marks = float(question.max_marks or 2)
        return {
            "score": 0.0,
            "max_marks": max_marks,
            "is_correct": False,
            "grading_mode": "AI_SUBJECTIVE",
            "explanation": "No answer was submitted.",
            "model_answer": question.correct_answer or "",
            "key_concepts": [],
            "missing_concepts": ["Complete answer"],
            "incorrect_concepts": [],
            "improvement_suggestions": "Write a structured answer covering definitions, key points, and an example.",
        }
    if llm_available():
        try:
            result = _llm_subjective(question, user_answer)
            if "AI-assisted" not in (result.get("explanation") or ""):
                result["explanation"] = (
                    (result.get("explanation") or "")
                    + " This is AI-assisted subjective evaluation, not official exam marking."
                ).strip()
            return result
        except Exception as exc:
            logger.warning(f"Subjective LLM grading failed: {type(exc).__name__}")
    return _keyword_subjective(question, user_answer)


def evaluate_question(question: Any, user_answer: str) -> Dict[str, Any]:
    if question.question_type in OBJECTIVE_TYPES:
        return grade_objective(question, user_answer)
    return grade_subjective(question, user_answer)
