"""Exam attempt lifecycle: generate, navigate, autosave, timer, submit."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.security import validate_difficulty, validate_positive_int
from database.academic_crud import (
    create_exam_attempt,
    finalize_attempt,
    get_answer_map,
    get_exam_attempt,
    save_evaluation,
    update_attempt_index,
    upsert_exam_answer,
)
from database.models import ExamAttempt, ExamQuestion
from services.evaluation_service import evaluate_question
from services.question_generator import generate_questions


def remaining_seconds(attempt: ExamAttempt) -> Optional[int]:
    if not attempt.time_limit_seconds:
        return None
    started = attempt.started_at
    if started is None:
        return attempt.time_limit_seconds
    if started.tzinfo is None:
        started = started.replace(tzinfo=timezone.utc)
    elapsed = int((datetime.now(timezone.utc) - started).total_seconds())
    return max(0, int(attempt.time_limit_seconds) - elapsed)


def is_expired(attempt: ExamAttempt) -> bool:
    rem = remaining_seconds(attempt)
    return rem is not None and rem <= 0 and attempt.status == "IN_PROGRESS"


def start_exam(
    db: Session,
    *,
    count: int = 5,
    question_types: Optional[List[str]] = None,
    difficulty: str = "medium",
    subject_id: Optional[int] = None,
    unit_number: Optional[int] = None,
    topic_name: Optional[str] = None,
    time_limit_minutes: Optional[int] = None,
    exam_kind: str = "practice",
    long_marks: float = 5.0,
    title: Optional[str] = None,
) -> ExamAttempt:
    count = validate_positive_int(count, "Number of questions", 1, 20)
    difficulty = validate_difficulty(difficulty)
    limit = None
    if time_limit_minutes:
        limit = validate_positive_int(time_limit_minutes, "Time limit (minutes)", 1, 240) * 60

    generated = generate_questions(
        count=count,
        question_types=question_types,
        difficulty=difficulty,
        subject_id=subject_id,
        unit_number=unit_number,
        topic_name=topic_name,
        long_marks=long_marks,
    )
    questions = generated["questions"]
    if not questions:
        raise ValueError("Could not generate questions. Add a subject or study material and try again.")

    kind_label = "Quiz" if exam_kind == "quiz" else "Exam" if exam_kind == "exam" else "Practice"
    return create_exam_attempt(
        db,
        title=title or f"{kind_label} — {difficulty.title()}",
        questions=questions,
        subject_id=subject_id,
        unit_number=unit_number,
        topic_name=topic_name,
        difficulty=difficulty,
        question_types=question_types,
        time_limit_seconds=limit,
        exam_kind=exam_kind,
        grounded=bool(generated.get("grounded")),
    )


def save_current_answer(db: Session, attempt_id: int, question_id: int, user_answer: str) -> None:
    attempt = get_exam_attempt(db, attempt_id)
    if not attempt or attempt.status != "IN_PROGRESS":
        return
    upsert_exam_answer(db, attempt_id, question_id, user_answer)


def goto_question(db: Session, attempt_id: int, index: int) -> Optional[ExamAttempt]:
    attempt = get_exam_attempt(db, attempt_id)
    if not attempt:
        return None
    max_i = max(0, len(attempt.questions) - 1)
    return update_attempt_index(db, attempt_id, min(max(index, 0), max_i))


def submit_exam(db: Session, attempt_id: int, expired: bool = False) -> ExamAttempt:
    attempt = get_exam_attempt(db, attempt_id)
    if not attempt:
        raise ValueError("Exam attempt not found.")
    if attempt.status in {"SUBMITTED", "EXPIRED"}:
        return attempt

    answers = get_answer_map(db, attempt.id)
    total = 0.0
    max_score = 0.0
    questions: List[ExamQuestion] = sorted(attempt.questions, key=lambda q: q.order_index)
    for question in questions:
        max_score += float(question.max_marks)
        user_ans = ""
        row = answers.get(question.id)
        if row:
            user_ans = row.user_answer or ""
        else:
            row = upsert_exam_answer(db, attempt.id, question.id, "")
        result = evaluate_question(question, user_ans)
        save_evaluation(
            db,
            row,
            score=result["score"],
            max_marks=result["max_marks"],
            is_correct=result["is_correct"],
            grading_mode=result["grading_mode"],
            key_concepts=result.get("key_concepts"),
            missing_concepts=result.get("missing_concepts"),
            incorrect_concepts=result.get("incorrect_concepts"),
            explanation=result.get("explanation"),
            model_answer=result.get("model_answer"),
            improvement_suggestions=result.get("improvement_suggestions"),
        )
        total += float(result["score"])

    accuracy = round((total / max_score) * 100, 1) if max_score else 0.0
    status = "EXPIRED" if expired else "SUBMITTED"
    finalized = finalize_attempt(
        db,
        attempt.id,
        status=status,
        total_score=round(total, 2),
        max_score=round(max_score, 2),
        accuracy=accuracy,
    )
    return finalized


def maybe_expire_and_submit(db: Session, attempt_id: int) -> ExamAttempt:
    attempt = get_exam_attempt(db, attempt_id)
    if not attempt:
        raise ValueError("Exam attempt not found.")
    if is_expired(attempt):
        return submit_exam(db, attempt_id, expired=True)
    return attempt


def attempt_overview(attempt: ExamAttempt) -> Dict[str, Any]:
    return {
        "id": attempt.id,
        "title": attempt.title,
        "status": attempt.status,
        "score": attempt.total_score,
        "max_score": attempt.max_score,
        "accuracy": attempt.accuracy,
        "difficulty": attempt.difficulty,
        "kind": attempt.exam_kind,
        "subject_id": attempt.subject_id,
        "topic_name": attempt.topic_name,
        "grounded": attempt.grounded,
        "started_at": attempt.started_at,
        "submitted_at": attempt.submitted_at,
        "remaining_seconds": remaining_seconds(attempt) if attempt.status == "IN_PROGRESS" else 0,
        "question_count": len(attempt.questions or []),
        "current_index": attempt.current_index,
    }
