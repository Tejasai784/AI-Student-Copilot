"""Academic report generation and export router."""
from __future__ import annotations

from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import ApiResponse
from database.models import User
from services.report_service import generate_exam_readiness_report

router = APIRouter(prefix="/api/v1/reports", tags=["Reports"])


@router.get("/exam-readiness", response_model=ApiResponse[Dict[str, Any]])
def get_exam_readiness(
    subject_id: Optional[int] = Query(None),
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Generates an academic readiness evaluation report for a subject or general course."""
    rep = generate_exam_readiness_report(db, subject_id=subject_id)
    if "overall_readiness_score" not in rep and "readiness_score" in rep:
        rep["overall_readiness_score"] = rep["readiness_score"]
    if "subject_name" not in rep and "subject" in rep:
        rep["subject_name"] = rep["subject"]
    return ApiResponse(success=True, data=rep)


@router.get("/download")
def download_report(
    subject_id: Optional[int] = Query(None),
    format: str = Query("markdown"),  # markdown | html
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Exports and downloads the readiness report as Markdown or HTML."""
    rep = generate_exam_readiness_report(db, subject_id=subject_id)
    if format.lower() == "html":
        content = rep.get("html_report", "<h1>Readiness Report</h1>")
        media_type = "text/html"
        filename = "exam_readiness_report.html"
    else:
        content = rep.get("markdown_report", "# Readiness Report")
        media_type = "text/markdown"
        filename = "exam_readiness_report.md"

    headers = {"Content-Disposition": f"attachment; filename={filename}"}
    return Response(content=content, media_type=media_type, headers=headers)
