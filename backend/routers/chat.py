"""AI Chat, Conversations, and Resilient SSE Streaming Router."""
from __future__ import annotations

import json
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator
from fastapi import APIRouter, Depends, HTTPException, status, Request, Query
from sqlalchemy.orm import Session
from sse_starlette.sse import EventSourceResponse

from backend.config import settings
from backend.logging_config import logger
from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import (
    ApiResponse,
    ChatQueryRequest,
    ChatQueryResponse,
    CitationItem,
    ChatStreamRequest,
    ConversationCreateRequest,
    ConversationUpdateRequest,
    ConversationResponse,
    MessageResponse,
)
from database.models import User, Conversation, Message
from database.crud import (
    create_conversation,
    get_conversations,
    get_conversation_by_id,
    update_conversation_title,
    delete_conversation,
    get_messages,
    add_message,
)
from services.tutor_service import (
    ask_tutor,
    TutorResponse,
    ANSWER_MODES,
    DEFAULT_ANSWER_MODE,
    _build_grounded_prompt,
    _build_general_prompt,
    _build_sources,
)
from rag.retriever import retrieve_chunks, build_context_block, RetrievalResult
from models.ai_provider import AIProviderManager

router = APIRouter(prefix="/api/v1/chat", tags=["Chat & AI Tutor"])


# ============================================================================
# Synchronous Chat Endpoint (Standard REST)
# ============================================================================

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
        conv = get_conversation_by_id(db, req.conversation_id)
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
            document_name=s.get("filename", s.get("document_name", "Study Material")),
            page_number=s.get("page_number", 1) if isinstance(s.get("page_number"), int) else 1,
            excerpt=s.get("excerpt", ""),
            chunk_id=str(s.get("chunk_index", s.get("chunk_id", "")))
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


# ============================================================================
# SSE Streaming Event Generator & Endpoints (GET + POST)
# ============================================================================

async def _stream_chat_events(
    request: Request,
    question: str,
    subject_id: Optional[int],
    style: str,
    conversation_id: Optional[int],
    db: Session,
    user_id: int
) -> AsyncGenerator[dict, None]:
    """Generates SSE events with keepalive, client disconnect detection, and mid-stream fallback."""
    # 1. Manage Conversation
    conv = None
    if conversation_id:
        conv = get_conversation_by_id(db, conversation_id)
    if not conv:
        conv = create_conversation(
            db=db,
            user_id=user_id,
            title=question[:60] if question else "Academic Chat",
            subject_id=subject_id
        )

    # 2. Record User Message
    add_message(
        db=db,
        conversation_id=conv.id,
        role="user",
        content=question
    )

    try:
        # Event: Initial Status
        yield {
            "event": "status",
            "data": json.dumps({"stage": "retrieving", "message": "Searching course materials..."})
        }

        # 3. Retrieve relevant chunks (RAG)
        retrieval: RetrievalResult = retrieve_chunks(
            query=question,
            top_k=settings.RAG_TOP_K,
            subject_id=subject_id,
            user_id=user_id
        )

        has_material = len(retrieval.chunks) > 0
        sources = _build_sources(retrieval.chunks)

        # Event: Sources / Citations
        if sources:
            yield {
                "event": "source",
                "data": json.dumps({"sources": sources})
            }

        # Event: Agent Step
        yield {
            "event": "agent_step",
            "data": json.dumps({
                "agent": "AI Tutor",
                "action": "Analyzing retrieved context and synthesizing grounded academic response"
            })
        }

        # 4. Prompt Assembly
        mode_instruction = ANSWER_MODES.get(style, ANSWER_MODES[DEFAULT_ANSWER_MODE])
        if has_material:
            context_block = build_context_block(retrieval.chunks)
            system_prompt, user_prompt = _build_grounded_prompt(question, context_block, mode_instruction)
        else:
            system_prompt, user_prompt = _build_general_prompt(question, mode_instruction)

        # Event: Status (generating)
        yield {
            "event": "status",
            "data": json.dumps({"stage": "generating", "message": "Streaming answer tokens..."})
        }

        # 5. Resilient token generation with mid-stream provider fallback
        mgr = AIProviderManager()
        full_answer = ""
        current_model = "local"

        for item in mgr.stream_text_with_resilience(
            prompt=user_prompt,
            system_instruction=system_prompt,
            temperature=0.3,
            max_tokens=2000
        ):
            if await request.is_disconnected():
                logger.info("Client disconnected from chat stream.")
                return

            itype = item.get("type")
            if itype == "provider_info":
                current_model = item.get("model", current_model)
                yield {
                    "event": "status",
                    "data": json.dumps({
                        "stage": "generating",
                        "provider": item.get("provider"),
                        "model": current_model
                    })
                }
            elif itype == "token":
                token_text = item.get("text", "")
                full_answer += token_text
                yield {
                    "event": "token",
                    "data": json.dumps({"text": token_text})
                }
                await asyncio.sleep(0.01)
            elif itype == "provider_switch":
                # Clear partial text so fallback starts clean without splicing
                full_answer = ""
                current_model = item.get("to_provider", "Offline")
                yield {
                    "event": "provider_switch",
                    "data": json.dumps(item)
                }
            elif itype == "done":
                current_model = item.get("model", current_model)

        # 6. Record Assistant Message in DB
        assistant_msg = add_message(
            db=db,
            conversation_id=conv.id,
            role="assistant",
            content=full_answer,
            agent_name=current_model,
            citations_json=json.dumps(sources) if sources else None
        )

        # Event: Done
        yield {
            "event": "done",
            "data": json.dumps({
                "conversation_id": conv.id,
                "message_id": assistant_msg.id,
                "model_used": current_model,
                "total_chars": len(full_answer),
                "finish_reason": "stop"
            })
        }

    except Exception as exc:
        logger.error(f"Error in chat stream: {exc}", exc_info=True)
        yield {
            "event": "error",
            "data": json.dumps({
                "code": "STREAMING_ERROR",
                "message": f"Streaming generation error: {str(exc)}"
            })
        }


@router.get("/stream")
async def stream_chat_get(
    request: Request,
    question: str = Query(..., min_length=1),
    subject_id: Optional[int] = Query(None),
    style: str = Query("Simple explanation"),
    conversation_id: Optional[int] = Query(None),
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Server-Sent Events (SSE) streaming endpoint for AI Tutor (GET query params)."""
    user_id = user.id if user else 1
    return EventSourceResponse(
        _stream_chat_events(
            request=request,
            question=question,
            subject_id=subject_id,
            style=style,
            conversation_id=conversation_id,
            db=db,
            user_id=user_id
        ),
        ping=15,
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


@router.post("/stream")
async def stream_chat_post(
    request: Request,
    body: ChatStreamRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Server-Sent Events (SSE) streaming endpoint for AI Tutor (POST JSON body)."""
    user_id = user.id if user else 1
    return EventSourceResponse(
        _stream_chat_events(
            request=request,
            question=body.question,
            subject_id=body.subject_id,
            style=body.style,
            conversation_id=body.conversation_id,
            db=db,
            user_id=user_id
        ),
        ping=15,
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# ============================================================================
# Conversation Management Endpoints (CRUD)
# ============================================================================

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
    req: Optional[ConversationCreateRequest] = None,
    title: Optional[str] = None,
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Creates a new chat session."""
    user_id = user.id if user else 1
    t = (req.title if req and req.title else title) or "New Conversation"
    s_id = (req.subject_id if req and req.subject_id is not None else subject_id)
    conv = create_conversation(db=db, user_id=user_id, title=t, subject_id=s_id)
    return ApiResponse(success=True, data=ConversationResponse.model_validate(conv))


@router.get("/conversations/{conversation_id}", response_model=ApiResponse[ConversationResponse])
def get_conversation_details(
    conversation_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves metadata for a specific conversation."""
    conv = get_conversation_by_id(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    return ApiResponse(success=True, data=ConversationResponse.model_validate(conv))


@router.patch("/conversations/{conversation_id}", response_model=ApiResponse[ConversationResponse])
def update_conversation(
    conversation_id: int,
    req: ConversationUpdateRequest,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Renames or updates an existing chat conversation."""
    user_id = user.id if user else 1
    conv = get_conversation_by_id(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    if conv.user_id and conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to edit this conversation.")
    updated = update_conversation_title(db, conversation_id, req.title)
    return ApiResponse(success=True, data=ConversationResponse.model_validate(updated))


@router.delete("/conversations/{conversation_id}", response_model=ApiResponse[Dict[str, Any]])
def remove_conversation(
    conversation_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Deletes a chat conversation and all associated messages."""
    user_id = user.id if user else 1
    conv = get_conversation_by_id(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    if conv.user_id and conv.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this conversation.")
    delete_conversation(db, conversation_id)
    return ApiResponse(success=True, data={"deleted": True, "conversation_id": conversation_id})


@router.get("/conversations/{conversation_id}/messages", response_model=ApiResponse[List[MessageResponse]])
def get_conversation_history(
    conversation_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves message history for a conversation."""
    conv = get_conversation_by_id(db, conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found.")
    msgs = get_messages(db, conversation_id=conversation_id)
    return ApiResponse(
        success=True,
        data=[MessageResponse.model_validate(m) for m in msgs]
    )
