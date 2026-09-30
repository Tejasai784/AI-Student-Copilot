from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from database.models import (
    StudentProfile, Subject, SyllabusTopic, Document, DocumentChunk,
    User, Conversation, Message, Goal, Task, AgentRun, ToolCall,
    Memory, Evaluation, ProgressRecord
)
from backend.logging_config import logger

# ============================================================================
# Student Profile CRUD
# ============================================================================

def get_student_profile(db: Session) -> Optional[StudentProfile]:
    """Retrieves the active student profile (first entry in single-user mode)."""
    return db.query(StudentProfile).first()

def create_or_update_student_profile(
    db: Session,
    name: str,
    course: str,
    branch: str,
    year: str,
    semester: str
) -> StudentProfile:
    """Creates or updates the single student profile."""
    profile = get_student_profile(db)
    if profile:
        profile.name = name.strip()
        profile.course = course.strip()
        profile.branch = branch.strip()
        profile.year = year.strip()
        profile.semester = semester.strip()
        logger.info(f"Updated student profile: {profile.name}")
    else:
        profile = StudentProfile(
            name=name.strip(),
            course=course.strip(),
            branch=branch.strip(),
            year=year.strip(),
            semester=semester.strip()
        )
        db.add(profile)
        logger.info(f"Created new student profile: {profile.name}")
    
    db.flush()
    return profile

# ============================================================================
# Subject CRUD
# ============================================================================

def get_subjects(db: Session) -> List[Subject]:
    """Returns all registered subjects ordered by name."""
    return db.query(Subject).order_by(Subject.name.asc()).all()

def get_subject_by_id(db: Session, subject_id: int) -> Optional[Subject]:
    """Finds a subject by its primary key."""
    return db.query(Subject).filter(Subject.id == subject_id).first()

def get_subject_by_code(db: Session, code: str) -> Optional[Subject]:
    """Finds a subject by code (case-insensitive)."""
    return db.query(Subject).filter(func.lower(Subject.code) == code.strip().lower()).first()

def create_subject(
    db: Session,
    name: str,
    code: str,
    semester: str,
    description: Optional[str] = None
) -> Subject:
    """Creates a new subject."""
    subject = Subject(
        name=name.strip(),
        code=code.strip().upper(),
        semester=semester.strip(),
        description=description.strip() if description else None
    )
    db.add(subject)
    db.flush()
    logger.info(f"Created subject: {subject.name} ({subject.code})")
    return subject

def update_subject(
    db: Session,
    subject_id: int,
    name: str,
    code: str,
    semester: str,
    description: Optional[str] = None
) -> Optional[Subject]:
    """Updates an existing subject."""
    subject = get_subject_by_id(db, subject_id)
    if not subject:
        return None
    subject.name = name.strip()
    subject.code = code.strip().upper()
    subject.semester = semester.strip()
    subject.description = description.strip() if description else None
    db.flush()
    logger.info(f"Updated subject {subject_id}: {subject.name}")
    return subject

def delete_subject(db: Session, subject_id: int) -> bool:
    """Deletes a subject and its associated topics (via cascade)."""
    subject = get_subject_by_id(db, subject_id)
    if not subject:
        return False
    db.delete(subject)
    db.flush()
    logger.info(f"Deleted subject ID {subject_id}")
    return True

# ============================================================================
# Syllabus Topic CRUD
# ============================================================================

def get_topics_by_subject(db: Session, subject_id: int) -> List[SyllabusTopic]:
    """Returns topics for a given subject ordered by unit number and id."""
    return db.query(SyllabusTopic).filter(
        SyllabusTopic.subject_id == subject_id
    ).order_by(SyllabusTopic.unit_number.asc(), SyllabusTopic.id.asc()).all()

def add_topic(
    db: Session,
    subject_id: int,
    unit_number: int,
    topic_name: str
) -> SyllabusTopic:
    """Adds a single topic to a subject."""
    topic = SyllabusTopic(
        subject_id=subject_id,
        unit_number=unit_number,
        topic_name=topic_name.strip()
    )
    db.add(topic)
    db.flush()
    logger.info(f"Added topic '{topic.topic_name}' (Unit {unit_number}) to subject {subject_id}")
    return topic

def bulk_add_topics(
    db: Session,
    subject_id: int,
    topics_data: List[Dict[str, Any]]
) -> List[SyllabusTopic]:
    """Adds multiple topics to a subject."""
    created_topics = []
    for item in topics_data:
        topic = SyllabusTopic(
            subject_id=subject_id,
            unit_number=int(item.get("unit_number", 1)),
            topic_name=item["topic_name"].strip(),
            is_completed=bool(item.get("is_completed", False))
        )
        db.add(topic)
        created_topics.append(topic)
    db.flush()
    logger.info(f"Bulk added {len(created_topics)} topics to subject {subject_id}")
    return created_topics

def toggle_topic_completion(db: Session, topic_id: int) -> Optional[SyllabusTopic]:
    """Toggles topic completion status."""
    topic = db.query(SyllabusTopic).filter(SyllabusTopic.id == topic_id).first()
    if topic:
        topic.is_completed = not topic.is_completed
        db.flush()
    return topic

def delete_topic(db: Session, topic_id: int) -> bool:
    """Deletes a single topic."""
    topic = db.query(SyllabusTopic).filter(SyllabusTopic.id == topic_id).first()
    if not topic:
        return False
    db.delete(topic)
    db.flush()
    return True

# ============================================================================
# Document CRUD
# ============================================================================

def create_document(
    db: Session,
    filename: str,
    stored_filename: str,
    file_path: str,
    file_size: int,
    subject_id: int,
    unit_number: Optional[int] = None,
    topic_name: Optional[str] = None,
    document_type: str = "Lecture Notes"
) -> Document:
    """Creates a new Document metadata record in PENDING status."""
    doc = Document(
        filename=filename,
        stored_filename=stored_filename,
        file_path=file_path,
        file_size=file_size,
        subject_id=subject_id,
        unit_number=unit_number,
        topic_name=topic_name.strip() if topic_name else None,
        document_type=document_type,
        status="PENDING"
    )
    db.add(doc)
    db.flush()
    logger.info(f"Created Document record: {doc.filename} (ID: {doc.id}) for Subject {subject_id}")
    return doc

def get_documents(db: Session, subject_id: Optional[int] = None) -> List[Document]:
    """Returns documents, optionally filtered by subject, ordered by creation date."""
    query = db.query(Document)
    if subject_id:
        query = query.filter(Document.subject_id == subject_id)
    return query.order_by(Document.created_at.desc()).all()

def get_document_by_id(db: Session, document_id: int) -> Optional[Document]:
    """Finds a document by ID."""
    return db.query(Document).filter(Document.id == document_id).first()

def update_document_status(
    db: Session,
    document_id: int,
    status: str,
    error_message: Optional[str] = None,
    total_pages: int = 0,
    total_chunks: int = 0
) -> Optional[Document]:
    """Updates document processing status and metrics."""
    doc = get_document_by_id(db, document_id)
    if not doc:
        return None
    doc.status = status
    doc.error_message = error_message
    if total_pages > 0:
        doc.total_pages = total_pages
    if total_chunks > 0:
        doc.total_chunks = total_chunks
    db.flush()
    logger.info(f"Updated Document {document_id} status to '{status}' (Pages: {total_pages}, Chunks: {total_chunks})")
    return doc

def delete_document_record(db: Session, document_id: int) -> bool:
    """Deletes document record and cascaded chunks from database."""
    doc = get_document_by_id(db, document_id)
    if not doc:
        return False
    # Explicitly remove child chunks to ensure deletion across all SQLite and PostgreSQL configurations
    db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).delete()
    db.delete(doc)
    db.flush()
    logger.info(f"Deleted Document ID {document_id}")
    return True

# ============================================================================
# Document Chunk CRUD
# ============================================================================

def bulk_add_document_chunks(db: Session, chunks_data: List[Dict[str, Any]]) -> List[DocumentChunk]:
    """Inserts a batch of document chunks."""
    created = []
    for item in chunks_data:
        chunk = DocumentChunk(
            document_id=item["document_id"],
            subject_id=item["subject_id"],
            unit_number=item.get("unit_number"),
            chunk_index=item["chunk_index"],
            page_number=item["page_number"],
            content=item["content"],
            char_count=item.get("char_count", len(item["content"])),
            vector_id=item["vector_id"]
        )
        db.add(chunk)
        created.append(chunk)
    db.flush()
    logger.info(f"Stored {len(created)} document chunks in DB.")
    return created

def get_document_chunks(db: Session, document_id: int) -> List[DocumentChunk]:
    """Returns chunks belonging to a document ordered by index."""
    return db.query(DocumentChunk).filter(
        DocumentChunk.document_id == document_id
    ).order_by(DocumentChunk.chunk_index.asc()).all()

# ============================================================================
# Dashboard Summary
# ============================================================================

def get_dashboard_summary(db: Session) -> Dict[str, Any]:
    """Calculates summary statistics for the dashboard."""
    profile = get_student_profile(db)
    subjects = get_subjects(db)
    total_subjects = len(subjects)
    
    total_topics = db.query(func.count(SyllabusTopic.id)).scalar() or 0
    completed_topics = db.query(func.count(SyllabusTopic.id)).filter(
        SyllabusTopic.is_completed.is_(True)
    ).scalar() or 0

    progress_percentage = (
        round((completed_topics / total_topics) * 100, 1) if total_topics > 0 else 0.0
    )

    total_materials = db.query(func.count(Document.id)).filter(
        Document.status == "COMPLETED"
    ).scalar() or 0

    from database.models import ExamAttempt, UpcomingExam, StudyTask
    from datetime import date as date_cls

    submitted = db.query(ExamAttempt).filter(ExamAttempt.status.in_(["SUBMITTED", "EXPIRED"])).all()
    quiz_accuracy = 0.0
    if submitted:
        quiz_accuracy = round(sum(a.accuracy for a in submitted) / len(submitted), 1)

    upcoming = db.query(func.count(UpcomingExam.id)).filter(
        UpcomingExam.exam_date >= date_cls.today()
    ).scalar() or 0

    today_tasks = db.query(func.count(StudyTask.id)).filter(
        StudyTask.scheduled_date == date_cls.today(),
        StudyTask.status == "PENDING",
    ).scalar() or 0

    return {
        "student_name": profile.name if profile else None,
        "course": profile.course if profile else None,
        "year": profile.year if profile else None,
        "semester": profile.semester if profile else None,
        "branch": profile.branch if profile else None,
        "total_subjects": total_subjects,
        "total_topics": total_topics,
        "completed_topics": completed_topics,
        "study_progress": progress_percentage,
        "total_materials": total_materials,
        "upcoming_exams": int(upcoming),
        "quiz_accuracy": float(quiz_accuracy),
        "weak_topics": [],
        "pending_tasks_today": int(today_tasks),
        "total_attempts": len(submitted),
    }


# ============================================================================
# Goal & Task CRUD
# ============================================================================

def create_goal(
    db: Session,
    title: str,
    objective: str,
    deadline: Optional[Any] = None,
    constraints: Optional[str] = None,
    required_resources: Optional[str] = None,
    subject_id: Optional[int] = None,
    user_id: Optional[int] = None,
    priority: int = 1
) -> Goal:
    goal = Goal(
        title=title.strip(),
        objective=objective.strip(),
        deadline=deadline,
        constraints=constraints,
        required_resources=required_resources,
        subject_id=subject_id,
        user_id=user_id,
        priority=priority,
        status="ACTIVE",
        progress_percentage=0.0
    )
    db.add(goal)
    db.flush()
    logger.info(f"Created goal: {goal.title} (ID: {goal.id})")
    return goal

def get_goals(db: Session, user_id: Optional[int] = None, status: Optional[str] = None) -> List[Goal]:
    query = db.query(Goal)
    if user_id:
        query = query.filter(Goal.user_id == user_id)
    if status:
        query = query.filter(Goal.status == status)
    return query.order_by(Goal.priority.asc(), Goal.created_at.desc()).all()

def get_goal_by_id(db: Session, goal_id: int) -> Optional[Goal]:
    return db.query(Goal).filter(Goal.id == goal_id).first()

def update_goal_progress(db: Session, goal_id: int) -> Optional[Goal]:
    goal = get_goal_by_id(db, goal_id)
    if not goal or not goal.tasks:
        return goal
    total = len(goal.tasks)
    completed = sum(1 for t in goal.tasks if t.status == "COMPLETED")
    goal.progress_percentage = round((completed / total) * 100.0, 1)
    if completed == total and total > 0:
        goal.status = "COMPLETED"
    db.flush()
    return goal

def create_task(
    db: Session,
    goal_id: Optional[int],
    title: str,
    description: Optional[str] = None,
    agent_assigned: str = "Study Agent",
    dependencies: Optional[str] = None,
    effort_estimate_minutes: int = 30,
    scheduled_date: Optional[Any] = None,
    order_index: int = 0
) -> Task:
    task = Task(
        goal_id=goal_id,
        title=title.strip(),
        description=description,
        agent_assigned=agent_assigned,
        dependencies=dependencies,
        effort_estimate_minutes=effort_estimate_minutes,
        scheduled_date=scheduled_date,
        order_index=order_index,
        status="PENDING"
    )
    db.add(task)
    db.flush()
    if goal_id:
        update_goal_progress(db, goal_id)
    return task

def update_task_status(db: Session, task_id: int, status: str, result_summary: Optional[str] = None) -> Optional[Task]:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return None
    task.status = status
    if result_summary:
        task.result_summary = result_summary
    db.flush()
    if task.goal_id:
        update_goal_progress(db, task.goal_id)
    return task

def toggle_task_completion(db: Session, task_id: int) -> Optional[Task]:
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        return None
    task.status = "COMPLETED" if task.status != "COMPLETED" else "PENDING"
    db.flush()
    if task.goal_id:
        update_goal_progress(db, task.goal_id)
    return task


# ============================================================================
# Conversation & Message CRUD
# ============================================================================

def create_conversation(db: Session, title: str = "New Conversation", user_id: Optional[int] = None, subject_id: Optional[int] = None) -> Conversation:
    conv = Conversation(
        title=title,
        user_id=user_id,
        subject_id=subject_id
    )
    db.add(conv)
    db.flush()
    return conv

def get_conversations(db: Session, user_id: Optional[int] = None, limit: int = 20) -> List[Conversation]:
    query = db.query(Conversation)
    if user_id:
        query = query.filter(Conversation.user_id == user_id)
    return query.order_by(Conversation.updated_at.desc()).limit(limit).all()

def get_conversation_by_id(db: Session, conv_id: int) -> Optional[Conversation]:
    return db.query(Conversation).filter(Conversation.id == conv_id).first()

def add_message(
    db: Session,
    conversation_id: int,
    role: str,
    content: str,
    agent_name: Optional[str] = None,
    tool_calls_json: Optional[str] = None,
    citations_json: Optional[str] = None
) -> Message:
    msg = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        agent_name=agent_name,
        tool_calls_json=tool_calls_json,
        citations_json=citations_json
    )
    db.add(msg)
    conv = get_conversation_by_id(db, conversation_id)
    if conv:
        from database.models import utc_now
        conv.updated_at = utc_now()
    db.flush()
    return msg

def get_messages(db: Session, conversation_id: int) -> List[Message]:
    return db.query(Message).filter(Message.conversation_id == conversation_id).order_by(Message.created_at.asc()).all()


# ============================================================================
# Memory CRUD
# ============================================================================

def save_memory(
    db: Session,
    key: str,
    value: str,
    memory_type: str = "preference",
    context: Optional[str] = None,
    confidence: float = 1.0,
    importance: int = 3,
    is_sensitive: bool = False,
    user_id: Optional[int] = None
) -> Memory:
    existing = db.query(Memory).filter(Memory.key == key.strip()).first()
    if existing:
        existing.value = value.strip()
        existing.memory_type = memory_type
        existing.context = context
        existing.confidence = confidence
        existing.importance = importance
        existing.is_sensitive = is_sensitive
        db.flush()
        return existing
    mem = Memory(
        user_id=user_id,
        memory_type=memory_type,
        key=key.strip(),
        value=value.strip(),
        context=context,
        confidence=confidence,
        importance=importance,
        is_sensitive=is_sensitive
    )
    db.add(mem)
    db.flush()
    return mem

def get_memories(db: Session, memory_type: Optional[str] = None, exclude_sensitive: bool = False) -> List[Memory]:
    query = db.query(Memory)
    if memory_type:
        query = query.filter(Memory.memory_type == memory_type)
    if exclude_sensitive:
        query = query.filter(Memory.is_sensitive == False)
    return query.order_by(Memory.importance.asc(), Memory.created_at.desc()).all()

def delete_memory(db: Session, memory_id: int) -> bool:
    mem = db.query(Memory).filter(Memory.id == memory_id).first()
    if mem:
        db.delete(mem)
        db.flush()
        return True
    return False


# ============================================================================
# Agent Run & Tool Call & Evaluation CRUD
# ============================================================================

def create_agent_run(db: Session, agent_name: str, input_query: str, plan_json: Optional[str] = None) -> AgentRun:
    run = AgentRun(
        agent_name=agent_name,
        input_query=input_query,
        plan_json=plan_json,
        status="RUNNING"
    )
    db.add(run)
    db.flush()
    return run

def finish_agent_run(
    db: Session,
    run_id: int,
    status: str,
    output_result: Optional[str] = None,
    execution_trace_json: Optional[str] = None,
    error_message: Optional[str] = None,
    retry_count: int = 0
) -> Optional[AgentRun]:
    run = db.query(AgentRun).filter(AgentRun.id == run_id).first()
    if not run:
        return None
    from database.models import utc_now
    run.status = status
    run.output_result = output_result
    run.execution_trace_json = execution_trace_json
    run.error_message = error_message
    run.retry_count = retry_count
    run.finished_at = utc_now()
    db.flush()
    return run

def log_tool_call(
    db: Session,
    tool_name: str,
    tool_input_json: str,
    tool_output_json: Optional[str] = None,
    status: str = "SUCCESS",
    execution_time_ms: float = 0.0,
    agent_run_id: Optional[int] = None
) -> ToolCall:
    tc = ToolCall(
        agent_run_id=agent_run_id,
        tool_name=tool_name,
        tool_input_json=tool_input_json,
        tool_output_json=tool_output_json,
        status=status,
        execution_time_ms=execution_time_ms
    )
    db.add(tc)
    db.flush()
    return tc

def save_evaluation(
    db: Session,
    agent_run_id: int,
    overall_score: float,
    factual_consistency: float = 1.0,
    completeness: float = 1.0,
    relevance: float = 1.0,
    feedback: Optional[str] = None,
    retry_required: bool = False,
    revision_notes: Optional[str] = None
) -> Evaluation:
    ev = Evaluation(
        agent_run_id=agent_run_id,
        overall_score=overall_score,
        factual_consistency=factual_consistency,
        completeness=completeness,
        relevance=relevance,
        feedback=feedback,
        retry_required=retry_required,
        revision_notes=revision_notes
    )
    db.add(ev)
    db.flush()
    return ev

def get_agent_runs(db: Session, limit: int = 20) -> List[AgentRun]:
    return db.query(AgentRun).order_by(AgentRun.started_at.desc()).limit(limit).all()
