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
    max_size_mb: Optional[int] = None
) -> Tuple[bool, str]:
    """
    Validates uploaded document for format, size, header integrity,
    MIME magic bytes, path safety, and rejects executable/macro code (.xlsm).
    Supports PDF, DOCX, TXT, MD, CSV, JSON.
    """
    if max_size_mb is None:
        max_size_mb = settings.MAX_FILE_SIZE_MB
    if not original_filename or "\x00" in original_filename:
        return False, "Invalid filename: contains forbidden characters."

    # Prevent path traversal
    if ".." in original_filename or "/" in original_filename or "\\" in original_filename:
        clean_name = Path(original_filename).name
        if ".." in original_filename:
            return False, "Path traversal sequence detected in filename."

    ext = Path(original_filename).suffix.lower()

    # Reject executable and macro formats
    FORBIDDEN_EXTENSIONS = {
        ".xlsm", ".xltm", ".xla", ".xlam", ".exe", ".bat", ".cmd",
        ".sh", ".vbs", ".ps1", ".dll", ".scr", ".msi", ".jar", ".com", ".pif"
    }
    if ext in FORBIDDEN_EXTENSIONS:
        return False, f"Forbidden file extension '{ext}'. Executable and macro-enabled files are strictly prohibited."

    if ext not in settings.ALLOWED_EXTENSIONS:
        allowed = ", ".join(settings.ALLOWED_EXTENSIONS)
        return False, f"Unsupported file format '{ext}'. Allowed formats: {allowed}"

    file_size = len(file_bytes)
    if file_size == 0:
        return False, "The uploaded file is empty (0 bytes)."

    max_bytes = max_size_mb * 1024 * 1024
    if file_size > max_bytes:
        return False, f"File size exceeds the {max_size_mb}MB limit ({file_size / (1024 * 1024):.1f}MB)."

    # Magic byte inspection by MIME type
    if ext == ".pdf":
        if not file_bytes.startswith(b"%PDF-"):
            return False, "Invalid PDF header. The file appears to be corrupted or not a valid PDF."
        if b"%%EOF" not in file_bytes[-2048:] and b"%%EOF" not in file_bytes:
            return False, "Corrupt PDF: Missing %%EOF marker."

    elif ext == ".docx":
        if not file_bytes.startswith(b"PK\x03\x04"):
            return False, "Invalid DOCX file header. Expected ZIP archive magic bytes."
        try:
            import zipfile, io
            with zipfile.ZipFile(io.BytesIO(file_bytes)) as zf:
                namelist = zf.namelist()
                if "[Content_Types].xml" not in namelist and "word/document.xml" not in namelist:
                    return False, "Invalid DOCX format: Missing essential document structures."
                for item in namelist:
                    if "vbaproject.bin" in item.lower() or item.lower().endswith(".bin"):
                        return False, "Forbidden: Macro or binary executable found inside document."
        except Exception:
            return False, "Corrupt DOCX file: Failed to read as valid ZIP archive."

    elif ext in (".txt", ".md", ".csv", ".json"):
        if file_bytes.startswith(b"MZ") or file_bytes.startswith(b"\x7fELF") or file_bytes.startswith(b"\xca\xfe\xba\xbe"):
            return False, "File disguised as text: Executable magic bytes detected."
        try:
            file_bytes.decode("utf-8")
        except UnicodeDecodeError:
            try:
                file_bytes.decode("latin-1")
            except UnicodeDecodeError:
                return False, "Text file is not readable as text encoding."

    return True, ""


def save_and_process_document(
    db: Session,
    file_bytes: bytes,
    original_filename: str,
    subject_id: int,
    unit_number: Optional[int] = None,
    topic_name: Optional[str] = None,
    document_type: str = "Lecture Notes",
    user_id: Optional[int] = None,
    ready_status: str = "COMPLETED"
) -> Document:
    """
    Saves document to data/uploads, creates metadata record, extracts text,
    splits into chunks, generates embeddings, and indexes into the vector store.
    """
    # 1. Validation
    is_valid, err_msg = validate_document_file(file_bytes, original_filename)
    if not is_valid:
        raise ValueError(err_msg)

    # 2. Secure file storage with UUID prefix and path containment check
    clean_base = sanitize_filename(Path(original_filename).stem)[:60]
    ext = Path(original_filename).suffix.lower() or ".txt"
    unique_id = uuid.uuid4().hex
    stored_filename = f"{unique_id}_{clean_base}{ext}"
    
    destination_path = (settings.UPLOAD_DIR / stored_filename).resolve()
    if not destination_path.is_relative_to(settings.UPLOAD_DIR.resolve()):
        raise ValueError("Invalid destination path: Path traversal detected.")

    with open(destination_path, "wb") as f:
        f.write(file_bytes)

    # 3. Create initial database record (PENDING)
    doc = create_document(
        db=db,
        filename=Path(original_filename).name,
        stored_filename=stored_filename,
        file_path=str(destination_path),
        file_size=len(file_bytes),
        subject_id=subject_id,
        unit_number=unit_number,
        topic_name=topic_name,
        document_type=document_type
    )
    if user_id:
        doc.user_id = user_id
        db.flush()

    # 4. Process document
    _execute_document_indexing(db, doc, destination_path, ready_status=ready_status)
    return doc


def _execute_document_indexing(
    db: Session,
    doc: Document,
    file_path: Path,
    ready_status: str = "COMPLETED"
) -> None:
    """Internal helper to extract, chunk, embed, and index a document."""
    try:
        update_document_status(db, doc.id, status="PROCESSING")

        # Extract text page by page (auto-detect format)
        pages = extract_text_from_file(file_path, doc.filename)
        total_pages = len(pages)

        # Chunk pages
        update_document_status(db, doc.id, status="INDEXING")
        chunks = chunk_document_pages(pages, chunk_size=600, chunk_overlap=80)
        total_chunks = len(chunks)

        if total_chunks == 0:
            raise DocumentExtractionError("No readable text could be extracted from this document (it may contain only scanned images or empty pages).")

        user_id = getattr(doc, "user_id", None) or 1
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
                "vector_id": v_id,
                "user_id": user_id
            })
            texts_to_embed.append(chunk_content)

        # Generate embeddings in batch
        embeddings = embedder.embed_batch(texts_to_embed)

        for rec, emb in zip(chunk_records, embeddings):
            item = dict(rec)
            item["topic_name"] = doc.topic_name
            item["embedding"] = emb
            vector_items.append(item)

        # Store in local vector store (with user_id)
        v_store = get_vector_store()
        v_store.add_chunks(vector_items)

        # Store chunk records in SQLite (strip user_id if column not in DB schema)
        db_chunk_records = [
            {k: v for k, v in rec.items() if k != "user_id"}
            for rec in chunk_records
        ]
        bulk_add_document_chunks(db, db_chunk_records)

        # Mark as completed / ready
        update_document_status(
            db,
            doc.id,
            status=ready_status,
            error_message=None,
            total_pages=total_pages,
            total_chunks=total_chunks
        )
        logger.info(f"Successfully processed and indexed document {doc.filename} (ID: {doc.id}, status: {ready_status})")

    except Exception as ex:
        err_str = str(ex)
        logger.error(f"Failed to process document {doc.id} ({doc.filename}): {err_str}", exc_info=True)
        update_document_status(db, doc.id, status="FAILED", error_message=err_str)


def process_document_background(document_id: int, ready_status: str = "READY") -> None:
    """
    Background worker function executed via FastAPI BackgroundTasks.
    Opens its own isolated DB session, runs the processing pipeline,
    and transitions statuses: UPLOADING -> PROCESSING -> INDEXING -> READY.
    """
    from database.database import get_db
    with get_db() as db:
        doc = get_document_by_id(db, document_id)
        if not doc:
            logger.error(f"Background task: Document {document_id} not found.")
            return
        file_path = Path(doc.file_path)
        if not file_path.exists():
            update_document_status(db, doc.id, status="FAILED", error_message="Source file not found on disk.")
            return
        _execute_document_indexing(db, doc, file_path, ready_status=ready_status)


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
