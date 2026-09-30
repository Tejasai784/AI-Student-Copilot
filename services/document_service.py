import uuid
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any
from sqlalchemy.orm import Session

from backend.config import settings
from backend.logging_config import logger
from utils.helpers import sanitize_filename
from database.crud import (
    create_document,
    get_document_by_id,
    update_document_status,
    delete_document_record,
    bulk_add_document_chunks,
    get_document_chunks
)
from database.models import Document
from rag.document_loader import extract_text_from_file, extract_text_from_pdf, DocumentExtractionError, PDFExtractionError
from rag.chunker import chunk_document_pages
from rag.embeddings import get_embedding_generator
from rag.vector_store import get_vector_store


def validate_pdf_file(
    file_bytes: bytes,
    original_filename: str,
    max_size_mb: int = settings.MAX_FILE_SIZE_MB
) -> Tuple[bool, str]:
    """Strictly validates PDF format."""
    if not original_filename.lower().endswith(".pdf"):
        return False, "Unsupported file format. Only PDF (.pdf) documents are accepted."
    file_size = len(file_bytes)
    if file_size == 0:
        return False, "The uploaded file is empty (0 bytes)."
    max_bytes = max_size_mb * 1024 * 1024
    if file_size > max_bytes:
        return False, f"File size exceeds the {max_size_mb}MB limit ({file_size / (1024 * 1024):.1f}MB)."
    if not file_bytes.startswith(b"%PDF-"):
        return False, "Invalid PDF header. The file appears to be corrupted or not a valid PDF."
    return True, ""


def validate_document_file(
    file_bytes: bytes,
    original_filename: str,
    max_size_mb: int = settings.MAX_FILE_SIZE_MB
) -> Tuple[bool, str]:
    """
    Validates uploaded document for format, size, and header integrity.
    Supports PDF, DOCX, TXT, MD, CSV, JSON.
    """
    ext = Path(original_filename).suffix.lower()
    if ext not in settings.ALLOWED_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_EXTENSIONS)
        return False, f"Unsupported file format '{ext}'. Allowed formats: {allowed}"

    file_size = len(file_bytes)
    if file_size == 0:
        return False, "The uploaded file is empty (0 bytes)."

    max_bytes = max_size_mb * 1024 * 1024
    if file_size > max_bytes:
        return False, f"File size exceeds the {max_size_mb}MB limit ({file_size / (1024 * 1024):.1f}MB)."

    # Verify PDF magic bytes header (%PDF-) if file is pdf
    if ext == ".pdf" and not file_bytes.startswith(b"%PDF-"):
        return False, "Invalid PDF header. The file appears to be corrupted or not a valid PDF."

    return True, ""


def save_and_process_document(
    db: Session,
    file_bytes: bytes,
    original_filename: str,
    subject_id: int,
    unit_number: Optional[int] = None,
    topic_name: Optional[str] = None,
    document_type: str = "Lecture Notes"
) -> Document:
    """
    Saves document to data/uploads, creates metadata record, extracts text,
    splits into chunks, generates embeddings, and indexes into the vector store.
    """
    # 1. Validation
    is_valid, err_msg = validate_document_file(file_bytes, original_filename)
    if not is_valid:
        raise ValueError(err_msg)

    # 2. Secure file storage
    clean_base = sanitize_filename(Path(original_filename).stem)
    ext = Path(original_filename).suffix.lower() or ".txt"
    unique_id = uuid.uuid4().hex[:8]
    stored_filename = f"{clean_base}_{unique_id}{ext}"
    
    destination_path = settings.UPLOAD_DIR / stored_filename
    with open(destination_path, "wb") as f:
        f.write(file_bytes)

    # 3. Create initial database record (PENDING)
    doc = create_document(
        db=db,
        filename=original_filename,
        stored_filename=stored_filename,
        file_path=str(destination_path),
        file_size=len(file_bytes),
        subject_id=subject_id,
        unit_number=unit_number,
        topic_name=topic_name,
        document_type=document_type
    )

    # 4. Process document
    _execute_document_indexing(db, doc, destination_path)
    return doc


def _execute_document_indexing(db: Session, doc: Document, file_path: Path) -> None:
    """Internal helper to extract, chunk, embed, and index a document."""
    try:
        update_document_status(db, doc.id, status="PROCESSING")

        # Extract text page by page (auto-detect format)
        pages = extract_text_from_file(file_path, doc.filename)
        total_pages = len(pages)

        # Chunk pages
        chunks = chunk_document_pages(pages, chunk_size=600, chunk_overlap=80)
        total_chunks = len(chunks)

        if total_chunks == 0:
            raise DocumentExtractionError("No readable text could be extracted from this document (it may contain only scanned images or empty pages).")

        # Prepare chunk data with vector IDs
        chunk_records = []
        texts_to_embed = []
        vector_items = []

        embedder = get_embedding_generator()

        for ch in chunks:
            v_id = f"doc_{doc.id}_chk_{ch['chunk_index']}"
            chunk_content = ch["content"]
            
            chunk_records.append({
                "document_id": doc.id,
                "subject_id": doc.subject_id,
                "unit_number": doc.unit_number,
                "chunk_index": ch["chunk_index"],
                "page_number": ch["page_number"],
                "content": chunk_content,
                "char_count": ch["char_count"],
                "vector_id": v_id
            })
            texts_to_embed.append(chunk_content)

        # Generate embeddings in batch
        embeddings = embedder.embed_batch(texts_to_embed)

        for rec, emb in zip(chunk_records, embeddings):
            item = dict(rec)
            item["topic_name"] = doc.topic_name
            item["embedding"] = emb
            vector_items.append(item)

        # Store in local vector store
        v_store = get_vector_store()
        v_store.add_chunks(vector_items)

        # Store chunk records in SQLite
        bulk_add_document_chunks(db, chunk_records)

        # Mark as completed
        update_document_status(
            db,
            doc.id,
            status="COMPLETED",
            error_message=None,
            total_pages=total_pages,
            total_chunks=total_chunks
        )
        logger.info(f"Successfully processed and indexed document {doc.filename} (ID: {doc.id})")

    except Exception as ex:
        err_str = str(ex)
        logger.error(f"Failed to process document {doc.id} ({doc.filename}): {err_str}", exc_info=True)
        update_document_status(db, doc.id, status="FAILED", error_message=err_str)


def retry_document_processing(db: Session, document_id: int) -> bool:
    """Retries processing for a previously failed document."""
    doc = get_document_by_id(db, document_id)
    if not doc:
        return False

    file_path = Path(doc.file_path)
    if not file_path.exists():
        update_document_status(db, doc.id, status="FAILED", error_message="Source PDF file not found on disk.")
        return False

    # Clean existing vector store chunks and DB chunks for this document
    v_store = get_vector_store()
    v_store.delete_by_document_id(doc.id)

    existing_chunks = get_document_chunks(db, doc.id)
    for c in existing_chunks:
        db.delete(c)
    db.flush()

    _execute_document_indexing(db, doc, file_path)
    return True


def delete_document_with_files(db: Session, document_id: int) -> bool:
    """
    Deletes a document from the database, removes physical file from disk,
    and removes indexed chunks from the vector store.
    """
    doc = get_document_by_id(db, document_id)
    if not doc:
        return False

    # 1. Remove physical file from disk if it exists
    try:
        fpath = Path(doc.file_path)
        if fpath.exists():
            fpath.unlink()
            logger.info(f"Deleted physical document file: {fpath}")
    except Exception as e:
        logger.warning(f"Could not delete physical file {doc.file_path}: {e}")

    # 2. Remove chunks from Vector Store
    try:
        v_store = get_vector_store()
        v_store.delete_by_document_id(doc.id)
    except Exception as e:
        logger.warning(f"Could not delete vector store entries for doc {doc.id}: {e}")

    # 3. Delete Document record and cascaded DocumentChunk rows in DB
    return delete_document_record(db, doc.id)
