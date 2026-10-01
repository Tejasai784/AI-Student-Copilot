"""Document upload, processing, and chunking router."""
from __future__ import annotations

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session

from backend.deps import get_db_session, get_optional_current_user
from backend.schemas import (
    ApiResponse,
    DocumentResponse,
    DocumentChunkResponse,
)
from database.models import User, Document, DocumentChunk
from database.crud import get_documents, get_document_by_id
from services.document_service import save_and_process_document, delete_document_with_files

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


@router.get("", response_model=ApiResponse[List[DocumentResponse]])
def list_documents(
    subject_id: Optional[int] = None,
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Retrieves uploaded documents, optionally filtered by subject."""
    docs = get_documents(db, subject_id=subject_id)
    return ApiResponse(
        success=True,
        data=[DocumentResponse.model_validate(d) for d in docs]
    )


@router.post("/upload", response_model=ApiResponse[DocumentResponse])
async def upload_document(
    file: UploadFile = File(...),
    subject_id: int = Form(...),
    unit_number: Optional[int] = Form(None),
    topic_name: Optional[str] = Form(None),
    document_type: str = Form("Lecture Notes"),
    db: Session = Depends(get_db_session),
    user: Optional[User] = Depends(get_optional_current_user)
):
    """Uploads and processes an academic document (PDF, DOCX, TXT)."""
    file_bytes = await file.read()
    if not file_bytes:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file is empty.")

    try:
        doc = save_and_process_document(
            db=db,
            file_bytes=file_bytes,
            original_filename=file.filename,
            subject_id=subject_id,
            unit_number=unit_number,
            topic_name=topic_name,
            document_type=document_type
        )
        if user and hasattr(doc, "user_id"):
            doc.user_id = user.id
            db.commit()

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
