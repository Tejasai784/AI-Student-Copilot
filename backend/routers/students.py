"""Student profile and dashboard router."""
from __future__ import annotations

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import ApiResponse, ProfileUpdateRequest, ProfileResponse
from database.models import User, StudentProfile, StudentSettings
from database.crud import (
    get_student_profile,
    create_or_update_student_profile,
    get_dashboard_summary
)
from database.academic_crud import get_student_settings, upsert_student_settings

router = APIRouter(prefix="/api/v1/students", tags=["Students"])


@router.get("/profile", response_model=ApiResponse[ProfileResponse])
def get_profile(
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves the student academic profile."""
    profile = get_student_profile(db)
    if not profile:
        profile = create_or_update_student_profile(
            db=db,
            name="Alex Mercer",
            course="B.Tech Computer Science & Engineering",
            branch="Computer Science",
            year="3rd Year",
            semester="6th Semester"
        )
    return ApiResponse(success=True, data=ProfileResponse.model_validate(profile))


@router.put("/profile", response_model=ApiResponse[ProfileResponse])
def update_profile(
    req: ProfileUpdateRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Updates the student academic profile."""
    profile = create_or_update_student_profile(
        db=db,
        name=req.name,
        course=req.course,
        branch=req.branch,
        year=req.year,
        semester=req.semester
    )
    return ApiResponse(success=True, data=ProfileResponse.model_validate(profile), message="Profile updated.")


@router.get("/settings", response_model=ApiResponse[Dict[str, Any]])
def get_settings_endpoint(
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves student learning preferences."""
    stg = get_student_settings(db)
    if not stg:
        stg = upsert_student_settings(db)
    return ApiResponse(
        success=True,
        data={
            "preferred_provider": stg.preferred_provider,
            "default_answer_style": stg.default_answer_style,
            "default_difficulty": stg.default_difficulty,
            "preferred_session_minutes": stg.preferred_session_minutes,
            "weekly_study_hours": stg.weekly_study_hours,
            "theme": stg.theme
        }
    )


class SettingsUpdateRequest(BaseModel):
    preferred_provider: Optional[str] = "auto"
    default_answer_style: Optional[str] = "Simple explanation"
    default_difficulty: Optional[str] = "medium"
    preferred_session_minutes: Optional[int] = 45
    weekly_study_hours: Optional[int] = 10
    theme: Optional[str] = "light"


@router.put("/settings", response_model=ApiResponse[Dict[str, Any]])
def update_settings_endpoint(
    req: SettingsUpdateRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Updates student learning preferences."""
    stg = upsert_student_settings(
        db=db,
        preferred_provider=req.preferred_provider,
        default_answer_style=req.default_answer_style,
        default_difficulty=req.default_difficulty,
        preferred_session_minutes=req.preferred_session_minutes,
        weekly_study_hours=req.weekly_study_hours,
        theme=req.theme
    )
    return ApiResponse(
        success=True,
        data={
            "preferred_provider": stg.preferred_provider,
            "default_answer_style": stg.default_answer_style,
            "default_difficulty": stg.default_difficulty,
            "preferred_session_minutes": stg.preferred_session_minutes,
            "weekly_study_hours": stg.weekly_study_hours,
            "theme": stg.theme
        },
        message="Preferences updated."
    )


@router.get("/dashboard", response_model=ApiResponse[Dict[str, Any]])
def get_dashboard(
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Returns overview metrics for dashboard."""
    summary = get_dashboard_summary(db)
    return ApiResponse(success=True, data=summary)
