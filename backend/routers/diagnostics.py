"""System health and infrastructure diagnostics router."""
from __future__ import annotations

import os
from datetime import datetime, timezone
from typing import Dict, Any, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from backend.config import settings
from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import ApiResponse
from database.models import User, Document, Subject, DocumentChunk
from rag.vector_store import get_vector_store

router = APIRouter(prefix="/api/v1/diagnostics", tags=["System Diagnostics"])


@router.get("/health", response_model=ApiResponse[Dict[str, Any]])
def health_check(db: Session = Depends(get_db_session)):
    """Liveness and readiness health check probe."""
    db_ok = False
    try:
        db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        db_ok = False

    vs = get_vector_store()
    vector_count = vs.count()

    return ApiResponse(
        success=db_ok,
        data={
            "status": "healthy" if db_ok else "unhealthy",
            "app_name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "database_connected": db_ok,
            "vector_store_indexed_chunks": vector_count,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
    )


@router.get("/system", response_model=ApiResponse[Dict[str, Any]])
def system_statistics(
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Returns platform storage and entity statistics."""
    doc_count = db.query(Document).count()
    subject_count = db.query(Subject).count()
    chunk_count = db.query(DocumentChunk).count()

    # Uploads disk size
    upload_bytes = 0
    if settings.UPLOAD_DIR.exists():
        for f in settings.UPLOAD_DIR.rglob("*"):
            if f.is_file():
                upload_bytes += f.stat().st_size

    vs = get_vector_store()

    return ApiResponse(
        success=True,
        data={
            "documents_count": doc_count,
            "subjects_count": subject_count,
            "document_chunks_count": chunk_count,
            "vector_store_count": vs.count(),
            "upload_storage_bytes": upload_bytes,
            "upload_storage_mb": round(upload_bytes / (1024 * 1024), 2),
            "database_url_masked": settings.DATABASE_URL.split("///")[-1] if "///" in settings.DATABASE_URL else "configured"
        }
    )
