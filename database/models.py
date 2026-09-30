from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Date, Float, ForeignKey
from sqlalchemy.orm import relationship
from database.database import Base

def utc_now():
    return datetime.now(timezone.utc)

class StudentProfile(Base):
    """Student profile model."""
    __tablename__ = "student_profiles"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    course = Column(String(100), nullable=False)
    branch = Column(String(100), nullable=False)
    year = Column(String(50), nullable=False)
    semester = Column(String(50), nullable=False)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    def __repr__(self) -> str:
        return f"<StudentProfile(id={self.id}, name='{self.name}', course='{self.course}')>"


class Subject(Base):
    """Subject/Course model."""
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    semester = Column(String(50), nullable=False)
    description = Column(Text, nullable=True)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    topics = relationship("SyllabusTopic", back_populates="subject", cascade="all, delete-orphan", lazy="selectin")
    documents = relationship("Document", back_populates="subject", cascade="all, delete-orphan", lazy="selectin")
    exam_attempts = relationship("ExamAttempt", back_populates="subject", cascade="all, delete-orphan", lazy="selectin")
    upcoming_exams = relationship("UpcomingExam", back_populates="subject", cascade="all, delete-orphan", lazy="selectin")
    study_tasks = relationship("StudyTask", back_populates="subject", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Subject(id={self.id}, code='{self.code}', name='{self.name}')>"


class SyllabusTopic(Base):
    """Syllabus unit/topic model."""
    __tablename__ = "syllabus_topics"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    unit_number = Column(Integer, nullable=False, default=1)
    topic_name = Column(String(255), nullable=False)
    is_completed = Column(Boolean, default=False, nullable=False)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    subject = relationship("Subject", back_populates="topics")

    def __repr__(self) -> str:
        return f"<SyllabusTopic(id={self.id}, unit={self.unit_number}, topic='{self.topic_name}')>"


class Document(Base):
    """Uploaded academic document model."""
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False, unique=True)
    file_path = Column(String(500), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    unit_number = Column(Integer, nullable=True)
    topic_name = Column(String(255), nullable=True)
    document_type = Column(String(50), default="Lecture Notes", nullable=False)
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING, PROCESSING, COMPLETED, FAILED
    error_message = Column(Text, nullable=True)
    total_pages = Column(Integer, default=0, nullable=False)
    total_chunks = Column(Integer, default=0, nullable=False)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    subject = relationship("Subject", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan", lazy="selectin")

    def __repr__(self) -> str:
        return f"<Document(id={self.id}, filename='{self.filename}', status='{self.status}')>"


class DocumentChunk(Base):
    """Segmented text chunk model for RAG and vector indexing."""
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, nullable=False, index=True)
    unit_number = Column(Integer, nullable=True, index=True)
    chunk_index = Column(Integer, nullable=False)
    page_number = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    char_count = Column(Integer, nullable=False)
    vector_id = Column(String(100), nullable=False, index=True)
    
    created_at = Column(DateTime, default=utc_now, nullable=False)

    # Relationships
    document = relationship("Document", back_populates="chunks")

    def __repr__(self) -> str:
        return f"<DocumentChunk(id={self.id}, doc_id={self.document_id}, page={self.page_number}, chunk={self.chunk_index})>"


class StudentSettings(Base):
    """Singleton-style student preferences (non-secret)."""
    __tablename__ = "student_settings"

    id = Column(Integer, primary_key=True, index=True)
    preferred_provider = Column(String(50), default="auto", nullable=False)  # auto | gemini | openai
    default_answer_style = Column(String(80), default="Simple explanation", nullable=False)
    default_difficulty = Column(String(20), default="medium", nullable=False)
    preferred_session_minutes = Column(Integer, default=45, nullable=False)
    weekly_study_hours = Column(Integer, default=10, nullable=False)
    theme = Column(String(20), default="light", nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)


class UpcomingExam(Base):
    """Scheduled exam / assessment date."""
    __tablename__ = "upcoming_exams"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    exam_date = Column(Date, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    subject = relationship("Subject", back_populates="upcoming_exams")


class ExamAttempt(Base):
    """A practice quiz or timed exam session."""
    __tablename__ = "exam_attempts"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False, default="Practice Exam")
    exam_kind = Column(String(30), nullable=False, default="practice")  # practice | quiz | exam
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="CASCADE"), nullable=True, index=True)
    unit_number = Column(Integer, nullable=True)
    topic_name = Column(String(255), nullable=True)
    difficulty = Column(String(20), nullable=False, default="medium")
    question_types = Column(Text, nullable=True)  # JSON list
    time_limit_seconds = Column(Integer, nullable=True)
    status = Column(String(30), nullable=False, default="IN_PROGRESS")  # IN_PROGRESS | SUBMITTED | EXPIRED
    current_index = Column(Integer, nullable=False, default=0)
    started_at = Column(DateTime, default=utc_now, nullable=False)
    submitted_at = Column(DateTime, nullable=True)
    total_score = Column(Float, nullable=False, default=0.0)
    max_score = Column(Float, nullable=False, default=0.0)
    accuracy = Column(Float, nullable=False, default=0.0)
    grounded = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    subject = relationship("Subject", back_populates="exam_attempts")
    questions = relationship("ExamQuestion", back_populates="attempt", cascade="all, delete-orphan", lazy="selectin")
    answers = relationship("ExamAnswer", back_populates="attempt", cascade="all, delete-orphan", lazy="selectin")


class ExamQuestion(Base):
    """A generated exam/practice question."""
    __tablename__ = "exam_questions"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    order_index = Column(Integer, nullable=False, default=0)
    question_type = Column(String(30), nullable=False)  # MCQ | MULTI_SELECT | TRUE_FALSE | SHORT | LONG | CODE
    question_text = Column(Text, nullable=False)
    options_json = Column(Text, nullable=True)
    correct_answer = Column(Text, nullable=True)
    max_marks = Column(Float, nullable=False, default=1.0)
    difficulty = Column(String(20), nullable=False, default="medium")
    topic_name = Column(String(255), nullable=True)
    unit_number = Column(Integer, nullable=True)
    subject_id = Column(Integer, nullable=True)
    source_excerpt = Column(Text, nullable=True)
    page_number = Column(Integer, nullable=True)
    document_id = Column(Integer, nullable=True)
    explanation = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    attempt = relationship("ExamAttempt", back_populates="questions")
    answers = relationship("ExamAnswer", back_populates="question", cascade="all, delete-orphan", lazy="selectin")


class ExamAnswer(Base):
    """Student answer plus evaluation for one question in an attempt."""
    __tablename__ = "exam_answers"

    id = Column(Integer, primary_key=True, index=True)
    attempt_id = Column(Integer, ForeignKey("exam_attempts.id", ondelete="CASCADE"), nullable=False, index=True)
    question_id = Column(Integer, ForeignKey("exam_questions.id", ondelete="CASCADE"), nullable=False, index=True)
    user_answer = Column(Text, nullable=True)
    is_correct = Column(Boolean, nullable=True)
    score = Column(Float, nullable=False, default=0.0)
    max_marks = Column(Float, nullable=False, default=1.0)
    grading_mode = Column(String(30), nullable=False, default="UNSCORED")  # OBJECTIVE | AI_SUBJECTIVE | UNSCORED
    key_concepts_json = Column(Text, nullable=True)
    missing_concepts_json = Column(Text, nullable=True)
    incorrect_concepts_json = Column(Text, nullable=True)
    explanation = Column(Text, nullable=True)
    model_answer = Column(Text, nullable=True)
    improvement_suggestions = Column(Text, nullable=True)
    evaluated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    attempt = relationship("ExamAttempt", back_populates="answers")
    question = relationship("ExamQuestion", back_populates="answers")


class StudyPlan(Base):
    """Generated daily/weekly study plan."""
    __tablename__ = "study_plans"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    horizon = Column(String(20), nullable=False, default="weekly")  # daily | weekly
    status = Column(String(20), nullable=False, default="ACTIVE")
    exam_focus = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    tasks = relationship("StudyTask", back_populates="plan", cascade="all, delete-orphan", lazy="selectin")


class StudyTask(Base):
    """A scheduled study / revision / practice task."""
    __tablename__ = "study_tasks"

    id = Column(Integer, primary_key=True, index=True)
    plan_id = Column(Integer, ForeignKey("study_plans.id", ondelete="CASCADE"), nullable=False, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    task_type = Column(String(30), nullable=False, default="STUDY")  # STUDY | REVISION | PRACTICE | EXAM_PREP
    topic_name = Column(String(255), nullable=True)
    unit_number = Column(Integer, nullable=True)
    scheduled_date = Column(Date, nullable=False)
    duration_minutes = Column(Integer, nullable=False, default=45)
    priority = Column(Integer, nullable=False, default=3)  # 1 highest
    status = Column(String(20), nullable=False, default="PENDING")  # PENDING | COMPLETED
    notes = Column(Text, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    plan = relationship("StudyPlan", back_populates="tasks")
    subject = relationship("Subject", back_populates="study_tasks")


class User(Base):
    """User account entity."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True, index=True)
    full_name = Column(String(150), nullable=True)
    role = Column(String(50), default="student", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    conversations = relationship("Conversation", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    goals = relationship("Goal", back_populates="user", cascade="all, delete-orphan", lazy="selectin")
    memories = relationship("Memory", back_populates="user", cascade="all, delete-orphan", lazy="selectin")


class Conversation(Base):
    """Chat session entity."""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False, default="New Conversation")
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", lazy="selectin", order_by="Message.created_at")


class Message(Base):
    """Chat message entity."""
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(50), nullable=False)  # user | assistant | system | agent
    content = Column(Text, nullable=False)
    agent_name = Column(String(100), nullable=True)
    tool_calls_json = Column(Text, nullable=True)
    citations_json = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    conversation = relationship("Conversation", back_populates="messages")


class Goal(Base):
    """Student high-level goal entity."""
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False)
    objective = Column(Text, nullable=False)
    deadline = Column(DateTime, nullable=True)
    constraints = Column(Text, nullable=True)  # JSON or text notes
    required_resources = Column(Text, nullable=True)
    priority = Column(Integer, default=1, nullable=False)  # 1 highest
    status = Column(String(50), default="ACTIVE", nullable=False)  # ACTIVE | COMPLETED | PAUSED | ABANDONED
    progress_percentage = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="goals")
    tasks = relationship("Task", back_populates="goal", cascade="all, delete-orphan", lazy="selectin", order_by="Task.order_index")


class Task(Base):
    """Decomposed subtask entity under a goal or autonomous agent execution."""
    __tablename__ = "tasks"

    id = Column(Integer, primary_key=True, index=True)
    goal_id = Column(Integer, ForeignKey("goals.id", ondelete="CASCADE"), nullable=True, index=True)
    order_index = Column(Integer, default=0, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    agent_assigned = Column(String(100), default="Study Agent", nullable=False)
    dependencies = Column(Text, nullable=True)  # JSON array of task ids
    effort_estimate_minutes = Column(Integer, default=30, nullable=False)
    scheduled_date = Column(Date, nullable=True)
    status = Column(String(50), default="PENDING", nullable=False)  # PENDING | IN_PROGRESS | COMPLETED | FAILED
    result_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    goal = relationship("Goal", back_populates="tasks")


class AgentRun(Base):
    """Execution run record for multi-agent workflows."""
    __tablename__ = "agent_runs"

    id = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(100), nullable=False, index=True)
    input_query = Column(Text, nullable=False)
    status = Column(String(50), default="RUNNING", nullable=False)  # RUNNING | SUCCESS | FAILED | REVISED
    plan_json = Column(Text, nullable=True)
    output_result = Column(Text, nullable=True)
    execution_trace_json = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime, default=utc_now, nullable=False)
    finished_at = Column(DateTime, nullable=True)

    tool_calls = relationship("ToolCall", back_populates="agent_run", cascade="all, delete-orphan", lazy="selectin")
    evaluations = relationship("Evaluation", back_populates="agent_run", cascade="all, delete-orphan", lazy="selectin")


class ToolCall(Base):
    """Tool invocation log for safety, audit, and explainability."""
    __tablename__ = "tool_calls"

    id = Column(Integer, primary_key=True, index=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    tool_name = Column(String(100), nullable=False, index=True)
    tool_input_json = Column(Text, nullable=False)
    tool_output_json = Column(Text, nullable=True)
    status = Column(String(50), default="SUCCESS", nullable=False)  # SUCCESS | FAILED | BLOCKED
    execution_time_ms = Column(Float, default=0.0, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    agent_run = relationship("AgentRun", back_populates="tool_calls")


class Memory(Base):
    """Student long-term memory entity."""
    __tablename__ = "memories"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    memory_type = Column(String(50), default="preference", nullable=False)  # preference | active_goal | fact | weakness | strength
    key = Column(String(150), nullable=False, index=True)
    value = Column(Text, nullable=False)
    context = Column(Text, nullable=True)
    confidence = Column(Float, default=1.0, nullable=False)
    importance = Column(Integer, default=3, nullable=False)  # 1 highest, 5 lowest
    is_sensitive = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(DateTime, default=utc_now, onupdate=utc_now, nullable=False)

    user = relationship("User", back_populates="memories")


class Evaluation(Base):
    """Critic and self-evaluation result."""
    __tablename__ = "evaluations"

    id = Column(Integer, primary_key=True, index=True)
    agent_run_id = Column(Integer, ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=True, index=True)
    factual_consistency = Column(Float, default=1.0, nullable=False)
    completeness = Column(Float, default=1.0, nullable=False)
    relevance = Column(Float, default=1.0, nullable=False)
    overall_score = Column(Float, default=1.0, nullable=False)
    feedback = Column(Text, nullable=True)
    retry_required = Column(Boolean, default=False, nullable=False)
    revision_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)

    agent_run = relationship("AgentRun", back_populates="evaluations")


class ProgressRecord(Base):
    """Periodic academic progress record."""
    __tablename__ = "progress_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id", ondelete="SET NULL"), nullable=True, index=True)
    record_date = Column(Date, nullable=False, index=True)
    topics_completed = Column(Integer, default=0, nullable=False)
    study_time_minutes = Column(Integer, default=0, nullable=False)
    quiz_accuracy = Column(Float, default=0.0, nullable=False)
    weak_topics_count = Column(Integer, default=0, nullable=False)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=utc_now, nullable=False)


# Aliases for specification compliance
Topic = SyllabusTopic
Quiz = ExamAttempt
Question = ExamQuestion
Answer = ExamAnswer
Embedding = DocumentChunk
