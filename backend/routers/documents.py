"""Document upload, processing, and chunking router."""
from __future__ import annotations

import uuid
from pathlib import Path
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form, BackgroundTasks, Query
from sqlalchemy.orm import Session

from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import (
    ApiResponse,
    DocumentResponse,
    DocumentChunkResponse,
    DocumentStatusResponse,
    DocumentSearchResponse,
    ValidatedCitationResponse,
)
from database.models import User, Document, DocumentChunk
from database.crud import get_documents, get_document_by_id, create_document
from services.document_service import (
    validate_document_file,
    save_and_process_document,
    delete_document_with_files,
    process_document_background,
)
from rag.retriever import retrieve_chunks, validate_citations
from utils.helpers import sanitize_filename
from backend.config import settings

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.get("", response_model=ApiResponse[List[DocumentResponse]])
def list_documents(
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves uploaded documents, optionally filtered by subject and scoped to current user."""
    query = db.query(Document)
    if subject_id is not None:
        query = query.filter(Document.subject_id == subject_id)
    if user and user.role != "admin":
        query = query.filter(Document.user_id.in_([user.id, 1]))
    docs = query.order_by(Document.created_at.desc()).all()

    return ApiResponse(
        success=True,
        data=[DocumentResponse.model_validate(d) for d in docs]
    )


@router.post("/upload", response_model=ApiResponse[DocumentResponse])
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    subject_id: int = Form(...),
    unit_number: Optional[int] = Form(None),
    topic_name: Optional[str] = Form(None),
    document_type: str = Form("Lecture Notes"),
    background: bool = Form(False),
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Uploads and processes an academic document (PDF, DOCX, TXT, MD, CSV, JSON).
    Hardened with MIME magic-byte validation, size limits, and path traversal protection.
    Supports asynchronous background task ingestion with pipeline status tracking.
    """
    filename = file.filename or "uploaded_document.txt"
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Uploaded file is empty (0 bytes)."
        )

    # 1. Strict validation (MIME magic bytes, size cap, traversal rejection, .xlsm macro rejection)
    is_valid, err_msg = validate_document_file(file_bytes, filename)
    if not is_valid:
        status_code = 413 if "exceeds" in err_msg else status.HTTP_400_BAD_REQUEST
        raise HTTPException(status_code=status_code, detail=err_msg)

    user_id = user.id if user else 1

    # 2. Asynchronous background task path
    if background:
        clean_base = sanitize_filename(Path(filename).stem)[:60]
        ext = Path(filename).suffix.lower() or ".txt"
        unique_id = uuid.uuid4().hex
        stored_filename = f"{unique_id}_{clean_base}{ext}"
        destination_path = (settings.UPLOAD_DIR / stored_filename).resolve()

        if not destination_path.is_relative_to(settings.UPLOAD_DIR.resolve()):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Path traversal sequence detected.")

        with open(destination_path, "wb") as f:
            f.write(file_bytes)

        # Create record in UPLOADING status
        doc = create_document(
            db=db,
            filename=Path(filename).name,
            stored_filename=stored_filename,
            file_path=str(destination_path),
            file_size=len(file_bytes),
            subject_id=subject_id,
            unit_number=unit_number,
            topic_name=topic_name,
            document_type=document_type
        )
        doc.user_id = user_id
        doc.status = "UPLOADING"
        db.commit()
        db.refresh(doc)

        # Dispatch background pipeline: UPLOADING -> PROCESSING -> INDEXING -> READY
        background_tasks.add_task(process_document_background, doc.id, "READY")

        return ApiResponse(
            success=True,
            data=DocumentResponse.model_validate(doc),
            message="Document uploaded. Processing in background."
        )

    # 3. Synchronous processing path
    try:
        doc = save_and_process_document(
            db=db,
            file_bytes=file_bytes,
            original_filename=filename,
            subject_id=subject_id,
            unit_number=unit_number,
            topic_name=topic_name,
            document_type=document_type,
            user_id=user_id,
            ready_status="READY"
        )
        return ApiResponse(
            success=True,
            data=DocumentResponse.model_validate(doc),
            message="Document uploaded and indexed successfully."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Document processing failed: {str(e)}"
        )


@router.get("/search", response_model=ApiResponse[DocumentSearchResponse])
def search_documents(
    query: str = Query(..., min_length=1),
    subject_id: Optional[int] = Query(None),
    unit_number: Optional[int] = Query(None),
    top_k: int = Query(5, ge=1, le=20),
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """
    Performs user-scoped vector retrieval with validated chunk citations.
    """
    user_id = user.id if user else 1
    retrieval = retrieve_chunks(
        query=query,
        top_k=top_k,
        subject_id=subject_id,
        unit_number=unit_number,
        user_id=user_id,
    )

    citations = validate_citations(retrieval.chunks)

    return ApiResponse(
        success=True,
        data=DocumentSearchResponse(
            query=query,
            total_results=len(retrieval.chunks),
            chunks=retrieval.chunks,
            citations=[ValidatedCitationResponse(**c) for c in citations],
            user_id=user_id
        )
    )


@router.get("/{document_id}/status", response_model=ApiResponse[DocumentStatusResponse])
def get_document_status(
    document_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves document pipeline status for polling (UPLOADING -> PROCESSING -> INDEXING -> READY/FAILED)."""
    doc = get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    return ApiResponse(
        success=True,
        data=DocumentStatusResponse(
            document_id=doc.id,
            status=doc.status,
            error_message=doc.error_message,
            total_pages=doc.total_pages,
            total_chunks=doc.total_chunks
        )
    )


@router.get("/{document_id}", response_model=ApiResponse[DocumentResponse])
def get_document(
    document_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves document details."""
    doc = get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return ApiResponse(success=True, data=DocumentResponse.model_validate(doc))


@router.delete("/{document_id}", response_model=ApiResponse[None])
def delete_document(
    document_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Deletes a document, its disk file, chunks, and vector index entries."""
    success = delete_document_with_files(db, document_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")
    return ApiResponse(success=True, data=None, message="Document deleted successfully.")


@router.get("/{document_id}/chunks", response_model=ApiResponse[List[DocumentChunkResponse]])
def get_document_chunks(
    document_id: int,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves the indexed chunks of a document."""
    doc = get_document_by_id(db, document_id)
    if not doc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found.")

    chunks = db.query(DocumentChunk).filter(DocumentChunk.document_id == document_id).order_by(DocumentChunk.chunk_index.asc()).all()
    return ApiResponse(
        success=True,
        data=[DocumentChunkResponse.model_validate(c) for c in chunks]
    )
