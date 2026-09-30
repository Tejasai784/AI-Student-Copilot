"""Adaptive study planner — heuristic, offline-safe, LLM-optional polish."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from database.academic_crud import (
    complete_study_task,
    create_study_plan,
    get_active_study_plan,
    get_tasks_for_date,
    get_upcoming_exams,
    update_study_task,
)
from database.crud import get_subjects
from services.analytics_service import detect_weak_topics, compute_performance
from services.llm_client import call_llm, llm_available


def _priority_topics(db: Session) -> List[Dict[str, Any]]:
    weak = detect_weak_topics(db)
    subjects = get_subjects(db)
    upcoming = get_upcoming_exams(db)
    urgent_ids = {e.subject_id for e in upcoming if e.exam_date <= date.today() + timedelta(days=7)}

    items: List[Dict[str, Any]] = []
    seen = set()
    for w in weak:
        key = (w.get("subject_id"), w.get("topic_name"))
        seen.add(key)
        items.append(
            {
                "subject_id": w.get("subject_id") or None,
                "topic_name": w.get("topic_name"),
                "priority": 1 if w.get("subject_id") in urgent_ids else 2,
                "reason": w.get("reason") or "Weak topic",
            }
        )
    for subj in subjects:
        for topic in subj.topics or []:
            key = (subj.id, topic.topic_name)
            if key in seen:
                continue
            pri = 2 if subj.id in urgent_ids else (4 if topic.is_completed else 3)
            items.append(
                {
                    "subject_id": subj.id,
                    "topic_name": topic.topic_name,
                    "unit_number": topic.unit_number,
                    "priority": pri,
                    "reason": "Upcoming exam" if subj.id in urgent_ids else "Syllabus coverage",
                }
            )
    if not items:
        items.append(
            {
                "subject_id": None,
                "topic_name": "General revision",
                "priority": 3,
                "reason": "No subjects yet — add a course to personalize this plan.",
            }
        )
    items.sort(key=lambda x: x["priority"])
    return items


def generate_study_plan(
    db: Session,
    *,
    horizon: str = "weekly",
    session_minutes: int = 45,
    weekly_hours: int = 10,
    exam_focus: Optional[str] = None,
) -> Any:
    horizon = "daily" if horizon == "daily" else "weekly"
    session_minutes = max(15, min(int(session_minutes), 180))
    weekly_hours = max(1, min(int(weekly_hours), 40))
    days = 1 if horizon == "daily" else 7
    sessions_per_day = max(1, round((weekly_hours * 60 / 7) / session_minutes))
    if horizon == "daily":
        sessions_per_day = max(1, min(sessions_per_day, 4))

    topics = _priority_topics(db)
    upcoming = get_upcoming_exams(db)
    focus = exam_focus
    if not focus and upcoming:
        first = upcoming[0]
        focus = f"{first.title} on {first.exam_date.isoformat()}"

    types_cycle = ["STUDY", "PRACTICE", "REVISION", "EXAM_PREP"]
    tasks: List[Dict[str, Any]] = []
    idx = 0
    for d in range(days):
        day = date.today() + timedelta(days=d)
        for s in range(int(sessions_per_day)):
            topic = topics[idx % len(topics)]
            ttype = types_cycle[(idx + d) % len(types_cycle)]
            if topic.get("priority", 3) <= 2 and s == 0:
                ttype = "EXAM_PREP" if upcoming else "REVISION"
            title = f"{ttype.replace('_', ' ').title()}: {topic.get('topic_name')}"
            tasks.append(
                {
                    "subject_id": topic.get("subject_id") or None,
                    "title": title,
                    "task_type": ttype,
                    "topic_name": topic.get("topic_name"),
                    "unit_number": topic.get("unit_number"),
                    "scheduled_date": day,
                    "duration_minutes": session_minutes,
                    "priority": int(topic.get("priority", 3)),
                    "notes": topic.get("reason"),
                }
            )
            idx += 1
            # Keep some balanced coverage: skip repeating same topic next slot
            if len(topics) > 1:
                idx += 0

    notes = (
        f"Prioritizes weak and exam-critical topics while rotating remaining syllabus. "
        f"Session length {session_minutes} min."
    )
    if llm_available():
        try:
            perf = compute_performance(db)
            text, _ = call_llm(
                f"Write a 3-sentence coaching note for a student. Weak topics: "
                f"{[w.get('topic_name') for w in detect_weak_topics(db)]}. "
                f"Overall accuracy {perf.get('overall_accuracy')}%. Horizon={horizon}.",
                "You are a study coach. Be practical and kind. No secrets.",
            )
            notes = (text or notes)[:800]
        except Exception:
            pass

    title = "Today's Study Plan" if horizon == "daily" else "Weekly Study Plan"
    return create_study_plan(
        db,
        title=title,
        horizon=horizon,
        tasks=tasks,
        exam_focus=focus,
        notes=notes,
    )


def today_plan(db: Session) -> List[Any]:
    return get_tasks_for_date(db, date.today())


def mark_task(db: Session, task_id: int, completed: bool = True):
    return complete_study_task(db, task_id, completed=completed)


def reschedule_task(db: Session, task_id: int, new_date: date, duration_minutes: Optional[int] = None):
    return update_study_task(db, task_id, scheduled_date=new_date, duration_minutes=duration_minutes)


def edit_task(db: Session, task_id: int, **kwargs):
    return update_study_task(db, task_id, **kwargs)
