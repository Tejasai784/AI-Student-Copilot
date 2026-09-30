"""Database package for AI Student Copilot."""
from database.database import Base, engine, get_db, init_db
from database.models import (
    StudentProfile,
    Subject,
    SyllabusTopic,
    Document,
    DocumentChunk,
    StudentSettings,
    UpcomingExam,
    ExamAttempt,
    ExamQuestion,
    ExamAnswer,
    StudyPlan,
    StudyTask,
)

__all__ = [
    "Base",
    "engine",
    "get_db",
    "init_db",
    "StudentProfile",
    "Subject",
    "SyllabusTopic",
    "Document",
    "DocumentChunk",
    "StudentSettings",
    "UpcomingExam",
    "ExamAttempt",
    "ExamQuestion",
    "ExamAnswer",
    "StudyPlan",
    "StudyTask",
]
