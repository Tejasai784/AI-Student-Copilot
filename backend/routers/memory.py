"""Student long-term memory router."""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import ApiResponse, MemoryCreateRequest, MemoryResponse
from database.models import User, Memory
from database.crud import save_memory, get_memories, delete_memory

router = APIRouter(prefix="/api/v1/memory", tags=["Memory"])


@router.get("", response_model=ApiResponse[List[MemoryResponse]])
def list_student_memories(
    memory_type: Optional[str] = None,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves long-term personalized memories for the student."""
    user_id = user.id if user else 1
    mems = get_memories(db, user_id=user_id, memory_type=memory_type)
    return ApiResponse(
        success=True,
        data=[MemoryResponse.model_validate(m) for m in mems]
    )


@router.post("", response_model=ApiResponse[MemoryResponse])
def add_student_memory(
    req: MemoryCreateRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Stores a new personalized learning memory fact or preference."""
    user_id = user.id if user else 1
    mem = save_memory(
        db=db,
        key=req.key,
        value=req.value,
        memory_type=req.memory_type,
        confidence=req.confidence,
        importance=req.importance,
        user_id=user_id
    )
    return ApiResponse(
        success=True,
        data=MemoryResponse.model_validate(mem),
        message="Memory saved."
    )


@router.delete("/{memory_id}", response_model=ApiResponse[None])
def remove_student_memory(
    memory_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Deletes a student memory entry."""
    success = delete_memory(db, memory_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Memory item not found.")
    return ApiResponse(success=True, data=None, message="Memory deleted.")
