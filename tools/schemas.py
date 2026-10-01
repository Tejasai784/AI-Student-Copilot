"""Pydantic Input and Output Schemas for Safe Agent Tools."""
from __future__ import annotations

from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ConfigDict


class BaseToolArgs(BaseModel):
    model_config = ConfigDict(extra="ignore")


class BaseToolOutput(BaseModel):
    ok: bool
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    summary: Optional[str] = None


# ============================================================================
# Individual Tool Argument Schemas
# ============================================================================

class CalculatorInput(BaseToolArgs):
    expression: str = Field(..., min_length=1, description="Mathematical expression to evaluate (e.g., '25 * 4 + sqrt(144)').")


class PythonSandboxInput(BaseToolArgs):
    code: str = Field(..., min_length=1, description="Python source code to execute safely.")
    timeout_seconds: float = Field(3.0, ge=0.5, le=30.0, description="Max execution duration in seconds.")


class DocumentReaderInput(BaseToolArgs):
    document_id: Optional[int] = Field(1, description="ID of the document to inspect.")
    page_number: Optional[int] = Field(None, description="Optional specific page number to retrieve.")
    max_pages: int = Field(5, ge=1, le=50, description="Maximum number of pages to read.")


class SemanticSearchInput(BaseToolArgs):
    query: str = Field(..., min_length=1, description="Natural language search query.")
    top_k: int = Field(4, ge=1, le=20, description="Maximum number of chunks to retrieve.")
    subject_id: Optional[int] = Field(None, description="Optional subject ID filter.")
    unit_number: Optional[int] = Field(None, description="Optional unit number filter.")


class TabularReaderInput(BaseToolArgs):
    file_path: str = Field(..., min_length=1, description="Path to CSV or tabular file.")
    preview_rows: int = Field(5, ge=1, le=100, description="Number of sample rows to preview.")
    max_rows: Optional[int] = Field(None, description="Alias for preview_rows.")

    def model_post_init(self, __context: Any) -> None:
        if self.max_rows is not None:
            self.preview_rows = self.max_rows


class WebResearchInput(BaseToolArgs):
    query: str = Field(..., min_length=1, description="Topic or query to research.")
    max_results: int = Field(3, ge=1, le=10, description="Number of articles/summaries to return.")
    num_results: Optional[int] = Field(None, description="Alias for max_results.")

    def model_post_init(self, __context: Any) -> None:
        if self.num_results is not None:
            self.max_results = self.num_results


class QuizGeneratorInput(BaseToolArgs):
    topic: str = Field("General", description="Topic for the generated quiz questions.")
    num_questions: int = Field(3, ge=1, le=20, description="Number of questions to generate.")
    count: Optional[int] = Field(None, description="Alias for num_questions.")
    difficulty: str = Field("medium", description="Difficulty level: easy, medium, hard.")
    subject_id: Optional[int] = Field(None, description="Target subject ID (optional).")

    def model_post_init(self, __context: Any) -> None:
        if self.count is not None:
            self.num_questions = self.count


class ReportGeneratorInput(BaseToolArgs):
    subject_name: str = Field("Course Material", description="Subject title, e.g. 'Python Programming'.")
    readiness_score: float = Field(85.0, ge=0.0, le=100.0, description="Calculated student readiness percentage.")
    weak_topics: Optional[List[str]] = Field(None, description="List of topics requiring revision.")
    subject_id: Optional[int] = Field(None, description="Target subject ID (optional).")


class TaskManagerInput(BaseToolArgs):
    action: str = Field("list_goals", description="Action to perform: list_goals, get_goal, create_subtask, complete_task.")
    goal_id: Optional[int] = Field(None, description="Goal ID (for get_goal or create_subtask).")
    task_id: Optional[int] = Field(None, description="Task ID (for complete_task).")
    task_title: Optional[str] = Field(None, description="Title when creating a subtask.")
    title: Optional[str] = Field(None, description="Alias for task_title.")
    subject_id: Optional[int] = Field(None, description="Optional subject ID.")

    def model_post_init(self, __context: Any) -> None:
        if self.title is not None and not self.task_title:
            self.task_title = self.title

