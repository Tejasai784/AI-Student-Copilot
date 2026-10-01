"""AI Chat and Tutor Router with SSE streaming support."""
from __future__ import annotations

import json
import asyncio
from typing import List, Optional, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import (
    ApiResponse,
    ChatQueryRequest,
    ChatQueryResponse,
    CitationItem,
    ConversationResponse,
    MessageResponse,
)
from database.models import User, Conversation, Message
from database.crud import (
    create_conversation,
    get_conversations,
    get_messages,
    add_message,
)
from services.tutor_service import ask_tutor, TutorResponse
from services.llm_client import get_gemini_diagnostics

router = APIRouter(prefix="/api/v1/chat", tags=["Chat & AI Tutor"])


@router.post("/ask", response_model=ApiResponse[ChatQueryResponse])
def ask_ai_tutor(
    req: ChatQueryRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Processes an academic query with RAG retrieval and LLM response."""
    user_id = user.id if user else 1

    # 1. Manage Conversation
    conv = None
    if req.conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == req.conversation_id).first()
    if not conv:
        conv = create_conversation(
            db=db,
            user_id=user_id,
            title=req.question[:60] if req.question else "Academic Chat",
            subject_id=req.subject_id
        )

    # 2. Record User Message
    add_message(
        db=db,
        conversation_id=conv.id,
        role="user",
        content=req.question
    )

    # 3. Call Tutor Service (RAG + AI Provider)
    tutor_resp: TutorResponse = ask_tutor(
        query=req.question,
        subject_id=req.subject_id,
        answer_mode=req.style,
        user_id=user_id
    )

    citations = [
        CitationItem(
            document_name=s.get("document_name", "Study Material"),
            page_number=s.get("page_number", 1),
            excerpt=s.get("excerpt", ""),
            chunk_id=str(s.get("chunk_id", ""))
        )
        for s in tutor_resp.sources
    ]

    # 4. Record Assistant Message
    add_message(
        db=db,
        conversation_id=conv.id,
        role="assistant",
        content=tutor_resp.answer,
        agent_name=tutor_resp.model_used,
        citations_json=json.dumps([c.model_dump() for c in citations]) if citations else None
    )

    return ApiResponse(
        success=True,
        data=ChatQueryResponse(
            answer=tutor_resp.answer,
            citations=citations,
            confidence_score=round(tutor_resp.retrieval_score or 0.85, 2),
            provider_used=tutor_resp.source_mode,
            model_used=tutor_resp.model_used,
            is_fallback=(tutor_resp.source_mode == "offline"),
            context_chunks_used=len(citations),
            conversation_id=conv.id
        )
    )


@router.get("/stream")
async def stream_chat(
    request: Request,
    question: str = Query(..., min_length=1),
    subject_id: Optional[int] = Query(None),
    style: str = Query("Simple explanation"),
    conversation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Server-Sent Events (SSE) streaming endpoint for AI Tutor."""
    user_id = user.id if user else 1

    # 1. Manage Conversation
    conv = None
    if conversation_id:
        conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        conv = create_conversation(
            db=db,
            user_id=user_id,
            title=question[:60],
            subject_id=subject_id
        )

    # Record User Message
    add_message(
        db=db,
        conversation_id=conv.id,
        role="user",
        content=question
    )

    async def event_generator() -> AsyncGenerator[dict, None]:
        # Emit initial ping / keepalive
        yield {"event": "ping", "data": json.dumps({"status": "connected"})}

        # Retrieve and process response
        tutor_resp: TutorResponse = ask_tutor(
            query=question,
            subject_id=subject_id,
            answer_mode=style,
            user_id=user_id
        )

        # Check disconnect
        if await request.is_disconnected():
            return

        # Emit provider info
        yield {
            "event": "start",
            "data": json.dumps({
                "provider": tutor_resp.source_mode,
                "model": tutor_resp.model_used,
                "conversation_id": conv.id
            })
        }

        # Emit citations
        if tutor_resp.sources:
            yield {
                "event": "citations",
                "data": json.dumps(tutor_resp.sources)
            }

        # Stream answer tokens (split by sentences / words for smooth SSE delivery)
        full_text = tutor_resp.answer
        words = full_text.split(" ")
        for i in range(0, len(words), 3):
            if await request.is_disconnected():
                return
            chunk = " ".join(words[i:i+3]) + " "
            yield {
                "event": "token",
                "data": json.dumps({"text": chunk})
            }
            await asyncio.sleep(0.02)  # smooth pacing

        # Record Assistant Message in DB
        add_message(
            db=db,
            conversation_id=conv.id,
            role="assistant",
            content=full_text,
            agent_name=tutor_resp.model_used,
            citations_json=json.dumps(tutor_resp.sources) if tutor_resp.sources else None
        )

        yield {
            "event": "done",
            "data": json.dumps({
                "conversation_id": conv.id,
                "model_used": tutor_resp.model_used
            })
        }

    return EventSourceResponse(event_generator(), ping=15)


@router.get("/conversations", response_model=ApiResponse[List[ConversationResponse]])
def list_conversations(
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves all chat conversations for the current student."""
    user_id = user.id if user else 1
    convs = get_conversations(db, user_id=user_id)
    return ApiResponse(
        success=True,
        data=[ConversationResponse.model_validate(c) for c in convs]
    )


@router.post("/conversations", response_model=ApiResponse[ConversationResponse])
def create_new_conversation(
    title: str = "New Conversation",
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Creates a new chat session."""
    user_id = user.id if user else 1
    conv = create_conversation(db=db, user_id=user_id, title=title, subject_id=subject_id)
    return ApiResponse(success=True, data=ConversationResponse.model_validate(conv))


@router.get("/conversations/{conversation_id}/messages", response_model=ApiResponse[List[MessageResponse]])
def get_conversation_history(
    conversation_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves message history for a conversation."""
    msgs = get_messages(db, conversation_id=conversation_id)
    return ApiResponse(
        success=True,
        data=[MessageResponse.model_validate(m) for m in msgs]
    )
