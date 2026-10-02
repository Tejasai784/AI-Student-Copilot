"""Adaptive study planner router."""
from __future__ import annotations

from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import (
    ApiResponse,
    PlanGenerateRequest,
    StudyPlanResponse,
    StudyTaskResponse,
)
from database.models import User, StudyPlan, StudyTask
from database.academic_crud import get_active_study_plan, complete_study_task
from services.planner_service import generate_study_plan

router = APIRouter(prefix="/api/v1/study-plan", tags=["Study Planner"])


@router.get("", response_model=ApiResponse[Optional[StudyPlanResponse]])
def get_current_plan(
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves the active study plan and its scheduled tasks."""
    plan = get_active_study_plan(db)
    if not plan:
        return ApiResponse(success=True, data=None, message="No active study plan found.")

    tasks = [StudyTaskResponse.model_validate(t) for t in sorted(plan.tasks, key=lambda x: (x.scheduled_date, x.priority))]
    plan_dict = {
        "id": plan.id,
        "title": plan.title,
        "horizon": plan.horizon,
        "status": plan.status,
        "exam_focus": plan.exam_focus,
        "notes": plan.notes,
        "tasks": tasks,
        "created_at": plan.created_at
    }
    return ApiResponse(success=True, data=StudyPlanResponse(**plan_dict))


@router.post("/generate", response_model=ApiResponse[StudyPlanResponse])
def generate_new_plan(
    req: PlanGenerateRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Generates an adaptive daily or weekly study schedule based on weak topics and syllabus."""
    plan = generate_study_plan(
        db=db,
        horizon=req.horizon,
        exam_focus=req.exam_focus,
        session_minutes=req.daily_minutes
    )
    if user and hasattr(plan, "user_id"):
        plan.user_id = user.id
        db.commit()

    tasks = [StudyTaskResponse.model_validate(t) for t in sorted(plan.tasks, key=lambda x: (x.scheduled_date, x.priority))]
    plan_dict = {
        "id": plan.id,
        "title": plan.title,
        "horizon": plan.horizon,
        "status": plan.status,
        "exam_focus": plan.exam_focus,
        "notes": plan.notes,
        "tasks": tasks,
        "created_at": plan.created_at
    }
    return ApiResponse(
        success=True,
        data=StudyPlanResponse(**plan_dict),
        message="New adaptive study plan generated successfully."
    )


@router.patch("/tasks/{task_id}/toggle", response_model=ApiResponse[StudyTaskResponse])
def toggle_task(
    task_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Toggles completion status for a study task."""
    task = db.query(StudyTask).filter(StudyTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Study task not found.")

    updated_task = complete_study_task(db, task_id)
    return ApiResponse(
        success=True,
        data=StudyTaskResponse.model_validate(updated_task),
        message=f"Task marked as {updated_task.status}."
    )
