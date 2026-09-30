"""Goal Understanding and Decomposition Service.
Parses natural language student goals into objectives, constraints, deadlines,
required resources, and converts them into structured tasks.
"""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone, date
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.logging_config import logger
from database.crud import (
    create_goal,
    create_task,
    get_goals,
    get_goal_by_id,
    get_subjects,
    save_memory
)
from database.models import Goal, Task
from services.llm_client import call_llm


def extract_deadline_days(text: str) -> Optional[int]:
    """Extracts duration in days from queries like 'in 7 days', 'next week', 'in 3 days'."""
    match = re.search(r"\b(\d+)\s*days?\b", text or "", re.I)
    if match:
        return int(match.group(1))
    if re.search(r"\b(next week|in a week|1 week)\b", text or "", re.I):
        return 7
    if re.search(r"\b(tomorrow|in 1 day|24 hours)\b", text or "", re.I):
        return 1
    if re.search(r"\b(weekend|2 days)\b", text or "", re.I):
        return 2
    return None


def parse_goal_intent(goal_text: str, subject_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Understands high-level student goal:
    - objective
    - constraints
    - deadline
    - required resources
    """
    days = extract_deadline_days(goal_text) or 7
    deadline_dt = datetime.now(timezone.utc) + timedelta(days=days)

    # Detect subject topic
    q_low = goal_text.lower()
    subject_hint = subject_name or "General Studies"
    if "python" in q_low:
        subject_hint = "Python Programming"
    elif "dbms" in q_low or "database" in q_low:
        subject_hint = "Database Management Systems"
    elif "os" in q_low or "operating system" in q_low:
        subject_hint = "Operating Systems"
    elif "math" in q_low or "calculus" in q_low:
        subject_hint = "Engineering Mathematics"
    elif "c++" in q_low or " c " in q_low:
        subject_hint = "C / Systems Programming"
    elif "java" in q_low:
        subject_hint = "Java Programming"

    constraints = [
        f"Available preparation window: {days} days",
        "Target study duration: 60-90 minutes daily",
        "Self-contained syllabus coverage with review and self-test"
    ]

    required_resources = [
        f"{subject_hint} Syllabus and Course Outline",
        "Lecture notes / reference documents",
        "Past exam papers and practice questions",
        "Interactive testing and weakness review"
    ]

    return {
        "title": f"Prepare for {subject_hint} Exam",
        "objective": f"Complete end-to-end exam preparation for {subject_hint} with topic mastery and mock evaluations.",
        "subject_hint": subject_hint,
        "days": days,
        "deadline": deadline_dt,
        "constraints": "; ".join(constraints),
        "required_resources": "; ".join(required_resources),
        "priority": 1 if days <= 7 else 2
    }


def create_goal_and_tasks_from_prompt(
    db: Session,
    prompt: str,
    subject_id: Optional[int] = None,
    user_id: Optional[int] = None
) -> Tuple[Goal, List[Task]]:
    """
    Main entry point: decomposes prompt into a persisted Goal and ordered Subtasks.
    """
    matched_subject = None
    if subject_id:
        from database.crud import get_subject_by_id
        subj = get_subject_by_id(db, subject_id)
        if subj:
            matched_subject = subj.name
    else:
        # Match from database
        subjects = get_subjects(db)
        p_low = prompt.lower()
        for s in subjects:
            if s.name.lower() in p_low or s.code.lower() in p_low:
                subject_id = s.id
                matched_subject = s.name
                break

    parsed = parse_goal_intent(prompt, subject_name=matched_subject)

    goal = create_goal(
        db=db,
        title=parsed["title"],
        objective=parsed["objective"],
        deadline=parsed["deadline"],
        constraints=parsed["constraints"],
        required_resources=parsed["required_resources"],
        subject_id=subject_id,
        user_id=user_id,
        priority=parsed["priority"]
    )

    # Decompose into multi-day tasks
    days = parsed["days"]
    today = date.today()
    created_tasks = []

    # Day 1: Syllabus inspection and fundamentals
    t1 = create_task(
        db=db,
        goal_id=goal.id,
        order_index=1,
        title=f"Inspect Syllabus & Core Concepts for {parsed['subject_hint']}",
        description="Extract syllabus topics, inspect course notes, and establish concept checklist.",
        agent_assigned="Study Agent",
        effort_estimate_minutes=60,
        scheduled_date=today
    )
    created_tasks.append(t1)

    # Day 2 to Day N-2: Deep topic study & practice
    t2 = create_task(
        db=db,
        goal_id=goal.id,
        order_index=2,
        title="Study Core Architecture, Syntax & Algorithms",
        description="Detailed review of primary units with coding examples and structural diagrams.",
        agent_assigned="Coding Agent" if "python" in prompt.lower() or "programming" in prompt.lower() else "Study Agent",
        effort_estimate_minutes=90,
        scheduled_date=today + timedelta(days=1)
    )
    created_tasks.append(t2)

    # Day N-1: Practice Questions & Mock Test
    t3 = create_task(
        db=db,
        goal_id=goal.id,
        order_index=3,
        title="Attempt Practice Questions & Mock Exam",
        description="Solve representative exam questions from past papers and receive automated grading.",
        agent_assigned="Exam Agent",
        effort_estimate_minutes=60,
        scheduled_date=today + timedelta(days=max(1, days - 2))
    )
    created_tasks.append(t3)

    # Day N: Weakness review & readiness report
    t4 = create_task(
        db=db,
        goal_id=goal.id,
        order_index=4,
        title="Weak Topic Revision & Final Readiness Report",
        description="Critic evaluation of weaknesses, re-testing missed questions, and generating readiness certificate.",
        agent_assigned="Critic Agent",
        effort_estimate_minutes=45,
        scheduled_date=today + timedelta(days=max(2, days - 1))
    )
    created_tasks.append(t4)

    # Save to student memory
    save_memory(
        db=db,
        key=f"active_goal_{goal.id}",
        value=f"Preparing for {parsed['subject_hint']} with target deadline {parsed['deadline'].strftime('%Y-%m-%d')}.",
        memory_type="active_goal",
        context=prompt,
        importance=1,
        user_id=user_id
    )

    logger.info(f"Generated Goal #{goal.id} with {len(created_tasks)} subtasks for prompt: {prompt}")
    return goal, created_tasks
