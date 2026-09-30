"""CRUD for exams, plans, settings, and scheduled exams."""
from __future__ import annotations

import json
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from backend.logging_config import logger
from database.models import (
    ExamAnswer,
    ExamAttempt,
    ExamQuestion,
    StudentSettings,
    StudyPlan,
    StudyTask,
    UpcomingExam,
    utc_now,
)


def _dumps(value: Any) -> Optional[str]:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False)


def _loads(raw: Optional[str], default: Any = None) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------

def get_student_settings(db: Session) -> Optional[StudentSettings]:
    return db.query(StudentSettings).first()


def upsert_student_settings(db: Session, **kwargs) -> StudentSettings:
    settings_row = get_student_settings(db)
    allowed = {
        "preferred_provider",
        "default_answer_style",
        "default_difficulty",
        "preferred_session_minutes",
        "weekly_study_hours",
        "theme",
    }
    if settings_row is None:
        settings_row = StudentSettings()
        db.add(settings_row)
        db.flush()
    for key, value in kwargs.items():
        if key in allowed and value is not None:
            setattr(settings_row, key, value)
    db.flush()
    return settings_row


# ---------------------------------------------------------------------------
# Upcoming exams
# ---------------------------------------------------------------------------

def create_upcoming_exam(
    db: Session,
    subject_id: int,
    title: str,
    exam_date: date,
    notes: Optional[str] = None,
) -> UpcomingExam:
    row = UpcomingExam(
        subject_id=subject_id,
        title=title.strip(),
        exam_date=exam_date,
        notes=notes.strip() if notes else None,
    )
    db.add(row)
    db.flush()
    return row


def get_upcoming_exams(db: Session, include_past: bool = False) -> List[UpcomingExam]:
    q = db.query(UpcomingExam)
    if not include_past:
        q = q.filter(UpcomingExam.exam_date >= date.today())
    return q.order_by(UpcomingExam.exam_date.asc()).all()


def delete_upcoming_exam(db: Session, exam_id: int) -> bool:
    row = db.query(UpcomingExam).filter(UpcomingExam.id == exam_id).first()
    if not row:
        return False
    db.delete(row)
    db.flush()
    return True


# ---------------------------------------------------------------------------
# Exam attempts
# ---------------------------------------------------------------------------

def create_exam_attempt(
    db: Session,
    title: str,
    questions: List[Dict[str, Any]],
    subject_id: Optional[int] = None,
    unit_number: Optional[int] = None,
    topic_name: Optional[str] = None,
    difficulty: str = "medium",
    question_types: Optional[List[str]] = None,
    time_limit_seconds: Optional[int] = None,
    exam_kind: str = "practice",
    grounded: bool = False,
) -> ExamAttempt:
    attempt = ExamAttempt(
        title=title.strip() or "Practice Exam",
        exam_kind=exam_kind,
        subject_id=subject_id,
        unit_number=unit_number,
        topic_name=topic_name,
        difficulty=difficulty,
        question_types=_dumps(question_types or []),
        time_limit_seconds=time_limit_seconds,
        status="IN_PROGRESS",
        grounded=grounded,
        max_score=float(sum(float(q.get("max_marks", 1)) for q in questions)),
        started_at=utc_now(),
    )
    db.add(attempt)
    db.flush()

    for idx, q in enumerate(questions):
        db.add(
            ExamQuestion(
                attempt_id=attempt.id,
                order_index=idx,
                question_type=q["question_type"],
                question_text=q["question_text"],
                options_json=_dumps(q.get("options")),
                correct_answer=_dumps(q.get("correct_answer"))
                if isinstance(q.get("correct_answer"), (list, dict))
                else (q.get("correct_answer") or ""),
                max_marks=float(q.get("max_marks", 1)),
                difficulty=q.get("difficulty", difficulty),
                topic_name=q.get("topic_name") or topic_name,
                unit_number=q.get("unit_number", unit_number),
                subject_id=q.get("subject_id", subject_id),
                source_excerpt=q.get("source_excerpt"),
                page_number=q.get("page_number"),
                document_id=q.get("document_id"),
                explanation=q.get("explanation"),
            )
        )
    db.flush()
    logger.info(f"Created exam attempt {attempt.id} with {len(questions)} questions.")
    return attempt


def get_exam_attempt(db: Session, attempt_id: int) -> Optional[ExamAttempt]:
    return db.query(ExamAttempt).filter(ExamAttempt.id == attempt_id).first()


def get_exam_attempts(db: Session, status: Optional[str] = None) -> List[ExamAttempt]:
    q = db.query(ExamAttempt)
    if status:
        q = q.filter(ExamAttempt.status == status)
    return q.order_by(ExamAttempt.created_at.desc()).all()


def get_in_progress_attempts(db: Session) -> List[ExamAttempt]:
    return get_exam_attempts(db, status="IN_PROGRESS")


def update_attempt_index(db: Session, attempt_id: int, index: int) -> Optional[ExamAttempt]:
    attempt = get_exam_attempt(db, attempt_id)
    if not attempt:
        return None
    attempt.current_index = max(0, index)
    db.flush()
    return attempt


def upsert_exam_answer(
    db: Session,
    attempt_id: int,
    question_id: int,
    user_answer: str,
) -> ExamAnswer:
    row = (
        db.query(ExamAnswer)
        .filter(ExamAnswer.attempt_id == attempt_id, ExamAnswer.question_id == question_id)
        .first()
    )
    if row is None:
        question = db.query(ExamQuestion).filter(ExamQuestion.id == question_id).first()
        row = ExamAnswer(
            attempt_id=attempt_id,
            question_id=question_id,
            max_marks=float(question.max_marks) if question else 1.0,
        )
        db.add(row)
    row.user_answer = user_answer
    db.flush()
    return row


def get_answer_map(db: Session, attempt_id: int) -> Dict[int, ExamAnswer]:
    rows = db.query(ExamAnswer).filter(ExamAnswer.attempt_id == attempt_id).all()
    return {r.question_id: r for r in rows}


def finalize_attempt(
    db: Session,
    attempt_id: int,
    status: str = "SUBMITTED",
    total_score: float = 0.0,
    max_score: float = 0.0,
    accuracy: float = 0.0,
) -> Optional[ExamAttempt]:
    attempt = get_exam_attempt(db, attempt_id)
    if not attempt:
        return None
    attempt.status = status
    attempt.submitted_at = utc_now()
    attempt.total_score = float(total_score)
    attempt.max_score = float(max_score)
    attempt.accuracy = float(accuracy)
    db.flush()
    return attempt


def save_evaluation(
    db: Session,
    answer: ExamAnswer,
    *,
    score: float,
    max_marks: float,
    is_correct: Optional[bool],
    grading_mode: str,
    key_concepts: Optional[List[str]] = None,
    missing_concepts: Optional[List[str]] = None,
    incorrect_concepts: Optional[List[str]] = None,
    explanation: Optional[str] = None,
    model_answer: Optional[str] = None,
    improvement_suggestions: Optional[str] = None,
) -> ExamAnswer:
    answer.score = float(score)
    answer.max_marks = float(max_marks)
    answer.is_correct = is_correct
    answer.grading_mode = grading_mode
    answer.key_concepts_json = _dumps(key_concepts or [])
    answer.missing_concepts_json = _dumps(missing_concepts or [])
    answer.incorrect_concepts_json = _dumps(incorrect_concepts or [])
    answer.explanation = explanation
    answer.model_answer = model_answer
    answer.improvement_suggestions = improvement_suggestions
    answer.evaluated_at = utc_now()
    db.flush()
    return answer


# ---------------------------------------------------------------------------
# Study plans
# ---------------------------------------------------------------------------

def create_study_plan(
    db: Session,
    title: str,
    horizon: str,
    tasks: List[Dict[str, Any]],
    exam_focus: Optional[str] = None,
    notes: Optional[str] = None,
    archive_previous: bool = True,
) -> StudyPlan:
    if archive_previous:
        for plan in db.query(StudyPlan).filter(StudyPlan.status == "ACTIVE").all():
            plan.status = "ARCHIVED"
    plan = StudyPlan(
        title=title.strip(),
        horizon=horizon,
        status="ACTIVE",
        exam_focus=exam_focus,
        notes=notes,
    )
    db.add(plan)
    db.flush()
    for item in tasks:
        db.add(
            StudyTask(
                plan_id=plan.id,
                subject_id=item.get("subject_id"),
                title=item["title"],
                task_type=item.get("task_type", "STUDY"),
                topic_name=item.get("topic_name"),
                unit_number=item.get("unit_number"),
                scheduled_date=item["scheduled_date"],
                duration_minutes=int(item.get("duration_minutes", 45)),
                priority=int(item.get("priority", 3)),
                notes=item.get("notes"),
            )
        )
    db.flush()
    logger.info(f"Created study plan {plan.id} with {len(tasks)} tasks.")
    return plan


def get_active_study_plan(db: Session) -> Optional[StudyPlan]:
    return (
        db.query(StudyPlan)
        .filter(StudyPlan.status == "ACTIVE")
        .order_by(StudyPlan.created_at.desc())
        .first()
    )


def get_study_plans(db: Session) -> List[StudyPlan]:
    return db.query(StudyPlan).order_by(StudyPlan.created_at.desc()).all()


def get_study_task(db: Session, task_id: int) -> Optional[StudyTask]:
    return db.query(StudyTask).filter(StudyTask.id == task_id).first()


def get_tasks_for_date(db: Session, day: date) -> List[StudyTask]:
    return (
        db.query(StudyTask)
        .filter(StudyTask.scheduled_date == day)
        .order_by(StudyTask.priority.asc(), StudyTask.id.asc())
        .all()
    )


def complete_study_task(db: Session, task_id: int, completed: bool = True) -> Optional[StudyTask]:
    task = get_study_task(db, task_id)
    if not task:
        return None
    task.status = "COMPLETED" if completed else "PENDING"
    task.completed_at = utc_now() if completed else None
    db.flush()
    return task


def update_study_task(
    db: Session,
    task_id: int,
    title: Optional[str] = None,
    scheduled_date: Optional[date] = None,
    duration_minutes: Optional[int] = None,
    notes: Optional[str] = None,
    priority: Optional[int] = None,
) -> Optional[StudyTask]:
    task = get_study_task(db, task_id)
    if not task:
        return None
    if title is not None and title.strip():
        task.title = title.strip()
    if scheduled_date is not None:
        task.scheduled_date = scheduled_date
    if duration_minutes is not None:
        task.duration_minutes = int(duration_minutes)
    if notes is not None:
        task.notes = notes
    if priority is not None:
        task.priority = int(priority)
    db.flush()
    return task
