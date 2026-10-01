"""Quizzes, practice tests, and exam evaluation router."""
from __future__ import annotations

import json
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import (
    ApiResponse,
    QuizGenerateRequest,
    ExamAttemptResponse,
    ExamQuestionResponse,
    QuizSubmitRequest,
)
from database.models import User, ExamAttempt, ExamQuestion, ExamAnswer
from services.exam_service import start_exam, submit_exam, get_exam_attempt, attempt_overview, upsert_exam_answer

router = APIRouter(prefix="/api/v1/quizzes", tags=["Quizzes & Exams"])


@router.post("/generate", response_model=ApiResponse[Dict[str, Any]])
def create_quiz(
    req: QuizGenerateRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Generates practice quiz or exam questions."""
    attempt = start_exam(
        db=db,
        count=req.num_questions,
        difficulty=req.difficulty,
        subject_id=req.subject_id,
        unit_number=req.unit_number,
        topic_name=req.topic_name,
        time_limit_minutes=(req.time_limit_seconds // 60) if req.time_limit_seconds else None,
        exam_kind=req.exam_kind
    )
    if user and hasattr(attempt, "user_id"):
        attempt.user_id = user.id
        db.commit()

    return ApiResponse(
        success=True,
        data=attempt_overview(attempt),
        message="Quiz generated successfully."
    )


@router.get("/{attempt_id}", response_model=ApiResponse[Dict[str, Any]])
def get_quiz_attempt(
    attempt_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves full details, questions, and answers for an exam attempt."""
    attempt = get_exam_attempt(db, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Quiz attempt not found.")

    overview = attempt_overview(attempt)
    # Include questions
    questions = []
    for q in sorted(attempt.questions, key=lambda x: x.order_index):
        options = []
        if q.options_json:
            try:
                options = json.loads(q.options_json)
            except Exception:
                options = []
        questions.append({
            "id": q.id,
            "order_index": q.order_index,
            "question_type": q.question_type,
            "question_text": q.question_text,
            "options": options,
            "max_marks": q.max_marks,
            "difficulty": q.difficulty,
            "topic_name": q.topic_name,
            "explanation": q.explanation if attempt.status in ["SUBMITTED", "EXPIRED"] else None,
            "correct_answer": q.correct_answer if attempt.status in ["SUBMITTED", "EXPIRED"] else None,
        })
    overview["questions"] = questions

    # Include answers if submitted
    answers = []
    for a in attempt.answers:
        answers.append({
            "question_id": a.question_id,
            "user_answer": a.user_answer,
            "is_correct": a.is_correct,
            "score": a.score,
            "max_marks": a.max_marks,
            "explanation": a.explanation,
            "model_answer": a.model_answer,
            "improvement_suggestions": a.improvement_suggestions
        })
    overview["answers"] = answers

    return ApiResponse(success=True, data=overview)


class AnswerSubmitRequest(BaseModel):
    question_id: int
    user_answer: str


@router.post("/{attempt_id}/answer", response_model=ApiResponse[None])
def record_single_answer(
    attempt_id: int,
    req: AnswerSubmitRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Saves or updates an answer for a specific question within an active attempt."""
    attempt = get_exam_attempt(db, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found.")
    if attempt.status != "IN_PROGRESS":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Attempt is already completed.")

    upsert_exam_answer(db, attempt_id, req.question_id, req.user_answer)
    db.commit()
    return ApiResponse(success=True, data=None, message="Answer recorded.")


@router.post("/{attempt_id}/submit", response_model=ApiResponse[Dict[str, Any]])
def submit_quiz_attempt(
    attempt_id: int,
    req: Optional[QuizSubmitRequest] = None,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Submits the exam, evaluates all answers, and calculates score."""
    attempt = get_exam_attempt(db, attempt_id)
    if not attempt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Exam attempt not found.")

    if req and req.answers:
        for q_id, u_ans in req.answers.items():
            upsert_exam_answer(db, attempt_id, int(q_id), u_ans)
        db.commit()

    finalized = submit_exam(db, attempt_id)
    return ApiResponse(
        success=True,
        data=attempt_overview(finalized),
        message="Exam submitted and evaluated successfully."
    )


@router.get("/history/list", response_model=ApiResponse[List[Dict[str, Any]]])
def get_quiz_history(
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Lists past quiz attempts."""
    query = db.query(ExamAttempt)
    if subject_id:
        query = query.filter(ExamAttempt.subject_id == subject_id)
    attempts = query.order_by(ExamAttempt.created_at.desc()).limit(50).all()

    return ApiResponse(
        success=True,
        data=[attempt_overview(a) for a in attempts]
    )
