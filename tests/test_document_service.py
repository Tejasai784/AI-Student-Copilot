import pytest
from pathlib import Path
from tests.pdf_test_utils import generate_minimal_pdf
from database.crud import (
    create_subject,
    get_documents,
    get_document_by_id,
    get_document_chunks,
    get_dashboard_summary
)
from services.document_service import (
    save_and_process_document,
    delete_document_with_files,
    retry_document_processing
)
from rag.vector_store import get_vector_store

def test_document_service_lifecycle(db_session):
    # Setup subject
    subj = create_subject(
        db=db_session,
        name="Database Management Systems",
        code="CS601",
        semester="6th Semester"
    )

    # 1. Generate valid 2-page PDF
    pdf_bytes = generate_minimal_pdf([
        "Unit 1: Relational Database Models and Constraints.",
        "Unit 2: Normalization and Lossless Join Decompositions."
    ])

    # 2. Save & Process document
    doc = save_and_process_document(
        db=db_session,
        file_bytes=pdf_bytes,
        original_filename="dbms_unit1_and_2.pdf",
        subject_id=subj.id,
        unit_number=1,
        document_type="Lecture Notes"
    )

    assert doc.id is not None
    assert doc.status == "COMPLETED"
    assert doc.total_pages == 2
    assert doc.total_chunks >= 2
    assert Path(doc.file_path).exists()

    # 3. Verify chunks stored in SQLite
    chunks = get_document_chunks(db_session, doc.id)
    assert len(chunks) == doc.total_chunks
    assert chunks[0].page_number == 1
    assert "Relational Database" in chunks[0].content

    # 4. Verify chunks indexed in Vector Store
    v_store = get_vector_store()
    doc_vectors = [m for m in v_store.metadata if m["document_id"] == doc.id]
    assert len(doc_vectors) == doc.total_chunks

    # 5. Check dashboard summary reflects total_materials
    summary = get_dashboard_summary(db_session)
    assert summary["total_materials"] == 1

    # 6. Delete document with files
    deleted = delete_document_with_files(db_session, doc.id)
    assert deleted is True

    # Verify removed from database
    assert get_document_by_id(db_session, doc.id) is None
    assert len(get_document_chunks(db_session, doc.id)) == 0

    # Verify physical file deleted
    assert not Path(doc.file_path).exists()

    # Verify removed from vector store
    remaining_doc_vectors = [m for m in v_store.metadata if m["document_id"] == doc.id]
    assert len(remaining_doc_vectors) == 0

def test_failed_document_graceful_handling(db_session):
    subj = create_subject(
        db=db_session,
        name="Operating Systems",
        code="CS602",
        semester="6th Semester"
    )

    # Malformed PDF bytes with valid header but corrupted trailer/stream
    corrupt_pdf_bytes = b"%PDF-1.4\nCorrupt trailer without catalog\n%%EOF"

    doc = save_and_process_document(
        db=db_session,
        file_bytes=corrupt_pdf_bytes,
        original_filename="corrupted_notes.pdf",
        subject_id=subj.id,
        unit_number=1,
        document_type="Lecture Notes"
    )

    assert doc.id is not None
    assert doc.status == "FAILED"
    assert doc.error_message is not None
    assert "Corrupt" in doc.error_message or "Error" in doc.error_message or "PDF" in doc.error_message

    # Clean up file created
    delete_document_with_files(db_session, doc.id)
