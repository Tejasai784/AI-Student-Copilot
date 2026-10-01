"""Subjects and syllabus management router."""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import (
    ApiResponse,
    SubjectCreateRequest,
    SubjectResponse,
    TopicCreateRequest,
    TopicResponse,
)
from database.models import User, Subject, SyllabusTopic
from database.crud import (
    get_subjects,
    get_subject_by_id,
    create_subject,
    add_topic,
    toggle_topic_completion,
)

router = APIRouter(prefix="/api/v1/subjects", tags=["Subjects"])


@router.get("", response_model=ApiResponse[List[SubjectResponse]])
def list_subjects(
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves all registered academic subjects."""
    subs = get_subjects(db)
    result = []
    for s in subs:
        total_topics = len(s.topics)
        completed = sum(1 for t in s.topics if t.is_completed)
        prog = (completed / total_topics * 100.0) if total_topics > 0 else 0.0
        result.append(
            SubjectResponse(
                id=s.id,
                name=s.name,
                code=s.code,
                semester=s.semester,
                description=s.description,
                topics_count=total_topics,
                completed_topics=completed,
                progress_percentage=round(prog, 1),
            )
        )
    return ApiResponse(success=True, data=result)


@router.post("", response_model=ApiResponse[SubjectResponse])
def create_new_subject(
    req: SubjectCreateRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Registers a new course subject."""
    sub = create_subject(
        db=db,
        name=req.name,
        code=req.code,
        semester=req.semester,
        description=req.description
    )
    if user and hasattr(sub, "user_id"):
        sub.user_id = user.id
        db.commit()

    return ApiResponse(
        success=True,
        data=SubjectResponse(
            id=sub.id,
            name=sub.name,
            code=sub.code,
            semester=sub.semester,
            description=sub.description,
            topics_count=0,
            completed_topics=0,
            progress_percentage=0.0
        ),
        message="Subject created successfully."
    )


@router.get("/{subject_id}", response_model=ApiResponse[dict])
def get_subject_details(
    subject_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves full details for a subject including its syllabus topics."""
    sub = get_subject_by_id(db, subject_id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    topics = [
        TopicResponse.model_validate(t).model_dump()
        for t in sorted(sub.topics, key=lambda x: (x.unit_number, x.id))
    ]
    total_topics = len(topics)
    completed = sum(1 for t in topics if t["is_completed"])
    prog = (completed / total_topics * 100.0) if total_topics > 0 else 0.0

    return ApiResponse(
        success=True,
        data={
            "id": sub.id,
            "name": sub.name,
            "code": sub.code,
            "semester": sub.semester,
            "description": sub.description,
            "topics": topics,
            "topics_count": total_topics,
            "completed_topics": completed,
            "progress_percentage": round(prog, 1),
            "documents_count": len(sub.documents)
        }
    )


@router.post("/{subject_id}/topics", response_model=ApiResponse[TopicResponse])
def add_subject_topic(
    subject_id: int,
    req: TopicCreateRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Adds a new topic to the subject's syllabus."""
    sub = get_subject_by_id(db, subject_id)
    if not sub:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Subject not found.")

    top = add_topic(
        db=db,
        subject_id=subject_id,
        unit_number=req.unit_number,
        topic_name=req.topic_name
    )
    return ApiResponse(
        success=True,
        data=TopicResponse.model_validate(top),
        message="Topic added successfully."
    )


@router.patch("/{subject_id}/topics/{topic_id}/toggle", response_model=ApiResponse[TopicResponse])
def toggle_topic(
    subject_id: int,
    topic_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Toggles completion status for a syllabus topic."""
    topic = toggle_topic_completion(db, topic_id)
    if not topic:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Topic not found.")
    return ApiResponse(
        success=True,
        data=TopicResponse.model_validate(topic),
        message=f"Topic marked as {'completed' if topic.is_completed else 'incomplete'}."
    )
