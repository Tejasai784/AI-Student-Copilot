"""Pydantic v2 schemas for API requests, responses, and standard envelopes."""
from __future__ import annotations

from typing import Generic, TypeVar, Optional, List, Any, Dict
from datetime import datetime, date
from pydantic import BaseModel, Field, ConfigDict

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard API response envelope."""
    success: bool = True
    data: Optional[T] = None
    error: Optional[str] = None
    message: Optional[str] = None


# ============================================================================
# Auth & User Schemas
# ============================================================================

class UserRegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: Optional[str] = None
    password: str = Field(..., min_length=6, max_length=100)
    full_name: Optional[str] = None


class UserLoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    refresh_token: Optional[str] = None
    expires_in: int


class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    full_name: Optional[str] = None
    role: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProfileUpdateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    course: str = Field(..., min_length=1, max_length=100)
    branch: str = "Computer Science"
    year: str = "3rd Year"
    semester: str = "6th Semester"


class ProfileResponse(BaseModel):
    id: int
    name: str
    course: str
    branch: str
    year: str
    semester: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Subjects & Syllabus Schemas
# ============================================================================

class TopicResponse(BaseModel):
    id: int
    subject_id: int
    unit_number: int
    topic_name: str
    is_completed: bool

    model_config = ConfigDict(from_attributes=True)


class TopicCreateRequest(BaseModel):
    unit_number: int = Field(1, ge=1, le=20)
    topic_name: str = Field(..., min_length=1, max_length=255)


class SubjectCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=150)
    code: str = Field(..., min_length=1, max_length=50)
    semester: str = Field(..., min_length=1, max_length=50)
    description: Optional[str] = None


class SubjectResponse(BaseModel):
    id: int
    name: str
    code: str
    semester: str
    description: Optional[str] = None
    topics_count: int = 0
    completed_topics: int = 0
    progress_percentage: float = 0.0

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Documents & RAG Schemas
# ============================================================================

class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_size: int
    subject_id: int
    unit_number: Optional[int] = None
    topic_name: Optional[str] = None
    document_type: str
    status: str
    total_pages: int
    total_chunks: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class DocumentChunkResponse(BaseModel):
    id: int
    document_id: int
    subject_id: int
    unit_number: Optional[int]
    page_number: int
    chunk_index: int
    content: str
    char_count: int

    model_config = ConfigDict(from_attributes=True)


class DocumentStatusResponse(BaseModel):
    document_id: int
    status: str
    error_message: Optional[str] = None
    total_pages: int = 0
    total_chunks: int = 0

    model_config = ConfigDict(from_attributes=True)


class ValidatedCitationResponse(BaseModel):
    source_id: str
    vector_id: str
    document_id: Optional[int] = None
    page_number: Any = 1
    chunk_index: int = 0
    topic_name: str = "General"
    score: float = 0.0
    user_id: Optional[int] = None
    char_count: int = 0
    excerpt: str = ""
    is_valid: bool = True
    is_cited: bool = True


class DocumentSearchResponse(BaseModel):
    query: str
    total_results: int
    chunks: List[Dict[str, Any]]
    citations: List[ValidatedCitationResponse]
    user_id: Optional[int] = None


# ============================================================================
# Chat & Tutor Schemas
# ============================================================================

class CitationItem(BaseModel):
    document_name: str
    page_number: int
    excerpt: str
    chunk_id: Optional[str] = None


class ChatQueryRequest(BaseModel):
    question: str = Field(..., min_length=1)
    subject_id: Optional[int] = None
    difficulty: str = "medium"
    style: str = "Simple explanation"
    conversation_id: Optional[int] = None


class ChatQueryResponse(BaseModel):
    answer: str
    citations: List[CitationItem] = []
    confidence_score: float = 0.85
    provider_used: str = "offline"
    model_used: str = "local"
    is_fallback: bool = False
    context_chunks_used: int = 0
    conversation_id: Optional[int] = None


class ConversationResponse(BaseModel):
    id: int
    title: str
    subject_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    agent_name: Optional[str] = None
    tool_calls_json: Optional[str] = None
    citations_json: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Goals & Autonomous Execution Schemas
# ============================================================================

class GoalCreateRequest(BaseModel):
    prompt: str = Field(..., min_length=5)
    subject_id: Optional[int] = None


class GoalResponse(BaseModel):
    id: int
    title: str
    objective: str
    subject_id: Optional[int] = None
    deadline: Optional[datetime] = None
    priority: int = 1
    status: str = "ACTIVE"
    progress_percentage: float = 0.0
    tasks_count: int = 0
    completed_tasks_count: int = 0
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class TaskResponse(BaseModel):
    id: int
    goal_id: Optional[int] = None
    order_index: int
    title: str
    description: Optional[str] = None
    agent_assigned: str
    effort_estimate_minutes: int
    status: str
    result_summary: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Study Plans & Quizzes
# ============================================================================

class PlanGenerateRequest(BaseModel):
    subject_id: Optional[int] = None
    horizon: str = "weekly"
    exam_focus: Optional[str] = None
    daily_minutes: int = 45


class StudyTaskResponse(BaseModel):
    id: int
    plan_id: int
    subject_id: Optional[int] = None
    title: str
    task_type: str
    topic_name: Optional[str] = None
    unit_number: Optional[int] = None
    scheduled_date: date
    duration_minutes: int
    priority: int
    status: str
    notes: Optional[str] = None
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class StudyPlanResponse(BaseModel):
    id: int
    title: str
    horizon: str
    status: str
    exam_focus: Optional[str] = None
    notes: Optional[str] = None
    tasks: List[StudyTaskResponse] = []
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class QuizGenerateRequest(BaseModel):
    subject_id: Optional[int] = None
    unit_number: Optional[int] = None
    topic_name: Optional[str] = None
    num_questions: int = Field(5, ge=1, le=30)
    difficulty: str = "medium"
    exam_kind: str = "practice"
    time_limit_seconds: Optional[int] = None


class ExamQuestionResponse(BaseModel):
    id: int
    order_index: int
    question_type: str
    question_text: str
    options: Optional[List[str]] = None
    max_marks: float
    difficulty: str
    topic_name: Optional[str] = None
    unit_number: Optional[int] = None
    explanation: Optional[str] = None


class ExamAttemptResponse(BaseModel):
    id: int
    title: str
    exam_kind: str
    subject_id: Optional[int] = None
    difficulty: str
    status: str
    total_score: float
    max_score: float
    accuracy: float
    grounded: bool
    questions: List[ExamQuestionResponse] = []
    started_at: datetime
    submitted_at: Optional[datetime] = None


class QuizSubmitRequest(BaseModel):
    answers: Dict[int, str]  # question_id -> user_answer


# ============================================================================
# Memory & Analytics Schemas
# ============================================================================

class MemoryCreateRequest(BaseModel):
    key: str = Field(..., min_length=1, max_length=150)
    value: str = Field(..., min_length=1)
    memory_type: str = "preference"
    confidence: float = 1.0
    importance: int = Field(3, ge=1, le=5)


class MemoryResponse(BaseModel):
    id: int
    memory_type: str
    key: str
    value: str
    confidence: float
    importance: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ProviderDiagnosticsResponse(BaseModel):
    gemini_configured: bool
    gemini_connection: str
    active_provider: str
    active_model: str
    fallback_models: List[str] = []
    openai_configured: bool = False
    openai_connection: str = "NOT CONFIGURED"
