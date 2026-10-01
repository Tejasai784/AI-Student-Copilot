"""Academic analytics, performance tracking, and weakness detection router."""
from __future__ import annotations

from typing import Dict, Any, List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import ApiResponse
from database.models import User
from services.analytics_service import (
    compute_performance,
    detect_weak_topics,
    generate_knowledge_map,
)

router = APIRouter(prefix="/api/v1/analytics", tags=["Analytics"])


@router.get("/performance", response_model=ApiResponse[Dict[str, Any]])
def get_performance_analytics(
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves aggregated performance analytics, accuracy trends, and subject mastery."""
    perf = compute_performance(db)
    return ApiResponse(success=True, data=perf)


@router.get("/weak-topics", response_model=ApiResponse[List[Dict[str, Any]]])
def get_weak_topics_list(
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Detects weak academic topics requiring targeted revision based on exam performance."""
    weak = detect_weak_topics(db)
    return ApiResponse(success=True, data=weak)


@router.get("/knowledge-map", response_model=ApiResponse[Dict[str, Any]])
def get_knowledge_map(
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Builds a subject/topic mastery graph representing the student's knowledge map."""
    km = generate_knowledge_map(db)
    return ApiResponse(success=True, data=km)
