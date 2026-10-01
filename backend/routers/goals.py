"""Goals decomposition and tracking router."""
from __future__ import annotations

from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import ApiResponse, GoalCreateRequest, GoalResponse, TaskResponse
from database.models import User, Goal, Task
from database.crud import get_goals, get_goal_by_id, toggle_task_completion
from services.goal_service import create_goal_and_tasks_from_prompt

router = APIRouter(prefix="/api/v1/goals", tags=["Goals & Tasks"])


@router.get("", response_model=ApiResponse[List[GoalResponse]])
def list_goals(
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves all academic goals and their progress for the student."""
    user_id = user.id if user else 1
    goals = get_goals(db, user_id=user_id)
    result = []
    for g in goals:
        total_tasks = len(g.tasks)
        completed = sum(1 for t in g.tasks if t.status == "COMPLETED")
        prog = (completed / total_tasks * 100.0) if total_tasks > 0 else 0.0
        result.append(
            GoalResponse(
                id=g.id,
                title=g.title,
                objective=g.objective,
                subject_id=g.subject_id,
                deadline=g.deadline,
                priority=g.priority,
                status=g.status,
                progress_percentage=round(prog, 1),
                tasks_count=total_tasks,
                completed_tasks_count=completed,
                created_at=g.created_at
            )
        )
    return ApiResponse(success=True, data=result)


@router.post("", response_model=ApiResponse[GoalResponse])
def create_goal_endpoint(
    req: GoalCreateRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Decomposes a student prompt into structured goals and actionable subtasks."""
    user_id = user.id if user else 1
    goal, tasks = create_goal_and_tasks_from_prompt(
        db=db,
        prompt=req.prompt,
        user_id=user_id,
        subject_id=req.subject_id
    )
    return ApiResponse(
        success=True,
        data=GoalResponse(
            id=goal.id,
            title=goal.title,
            objective=goal.objective,
            subject_id=goal.subject_id,
            deadline=goal.deadline,
            priority=goal.priority,
            status=goal.status,
            progress_percentage=goal.progress_percentage,
            tasks_count=len(tasks),
            completed_tasks_count=0,
            created_at=goal.created_at
        ),
        message="Goal created and decomposed into tasks."
    )


@router.get("/{goal_id}", response_model=ApiResponse[Dict[str, Any]])
def get_goal_details(
    goal_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves full goal details including its decomposed subtasks."""
    goal = get_goal_by_id(db, goal_id)
    if not goal:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Goal not found.")

    tasks = [
        TaskResponse.model_validate(t).model_dump()
        for t in sorted(goal.tasks, key=lambda x: x.order_index)
    ]
    total_tasks = len(tasks)
    completed = sum(1 for t in tasks if t["status"] == "COMPLETED")
    prog = (completed / total_tasks * 100.0) if total_tasks > 0 else 0.0

    return ApiResponse(
        success=True,
        data={
            "id": goal.id,
            "title": goal.title,
            "objective": goal.objective,
            "subject_id": goal.subject_id,
            "deadline": goal.deadline.isoformat() if goal.deadline else None,
            "priority": goal.priority,
            "status": goal.status,
            "progress_percentage": round(prog, 1),
            "tasks": tasks,
            "tasks_count": total_tasks,
            "completed_tasks_count": completed,
            "created_at": goal.created_at.isoformat()
        }
    )


@router.patch("/tasks/{task_id}/toggle", response_model=ApiResponse[TaskResponse])
def toggle_subtask(
    task_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Toggles completion status for a decomposed goal task."""
    task = toggle_task_completion(db, task_id)
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found.")
    return ApiResponse(
        success=True,
        data=TaskResponse.model_validate(task),
        message=f"Task marked as {task.status}."
    )
