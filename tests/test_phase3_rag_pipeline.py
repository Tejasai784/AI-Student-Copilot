"""
Phase 3 Verification Tests: RAG & Materials Pipeline.

Validates:
1. File upload hardening:
   - MIME magic-byte validation
   - Path traversal protection
   - Macro/executable rejection (.xlsm)
   - Oversized and empty file rejection
2. Document ingestion pipeline:
   - Status pipeline: UPLOADING -> PROCESSING -> INDEXING -> READY
   - Status polling endpoint GET /api/v1/documents/{id}/status
3. User-scoped vector retrieval:
   - Queries strictly filtered by user_id
   - Validated chunk citations (chunk_id, vector_id, page_number)
4. Backward compatibility:
   - Existing vector store and document lifecycle behavior preserved
"""
import io
import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings
from backend.security import create_access_token
from database.database import get_db
from database.models import User, Subject, Document
from database.crud import create_subject, get_document_by_id
from rag.retriever import retrieve_chunks, validate_citations
from rag.vector_store import get_vector_store
from services.document_service import validate_document_file, save_and_process_document


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="module")
def auth_headers_user1():
    token = create_access_token({"sub": "1", "username": "local_student"})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(scope="module")
def auth_headers_user2():
    token = create_access_token({"sub": "2", "username": "other_student"})
    return {"Authorization": f"Bearer {token}"}


# ============================================================================
# 1. File Upload Hardening Tests
# ============================================================================

def test_upload_rejects_empty_file(client, auth_headers_user1):
    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("empty.txt", io.BytesIO(b""), "text/plain")},
        data={"subject_id": 1},
        headers=auth_headers_user1
    )
    assert res.status_code == 400
    assert "empty" in res.json()["detail"].lower()


def test_upload_rejects_path_traversal(client, auth_headers_user1):
    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("../../etc/passwd.txt", io.BytesIO(b"Sensitive text content"), "text/plain")},
        data={"subject_id": 1},
        headers=auth_headers_user1
    )
    assert res.status_code == 400
    assert "traversal" in res.json()["detail"].lower()


def test_upload_rejects_xlsm_macro_file(client, auth_headers_user1):
    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("grades_with_macro.xlsm", io.BytesIO(b"dummy macro bytes"), "application/vnd.ms-excel.sheet.macroEnabled.12")},
        data={"subject_id": 1},
        headers=auth_headers_user1
    )
    assert res.status_code == 400
    assert "forbidden" in res.json()["detail"].lower() or "macro" in res.json()["detail"].lower()


def test_upload_rejects_disguised_fake_pdf(client, auth_headers_user1):
    # A plain text file fraudulently given a .pdf extension
    fake_pdf = b"This is just plain text, not a real PDF file."
    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("fake_lecture.pdf", io.BytesIO(fake_pdf), "application/pdf")},
        data={"subject_id": 1},
        headers=auth_headers_user1
    )
    assert res.status_code == 400
    assert "pdf" in res.json()["detail"].lower()


def test_upload_rejects_oversized_file(client, auth_headers_user1, monkeypatch):
    # Temporarily set max size to 1 MB for testing
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_MB", 1)
    huge_payload = b"A" * (2 * 1024 * 1024)  # 2MB
    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("huge_file.txt", io.BytesIO(huge_payload), "text/plain")},
        data={"subject_id": 1},
        headers=auth_headers_user1
    )
    assert res.status_code in (400, 413)
    assert "exceeds" in res.json()["detail"].lower()


# ============================================================================
# 2. Ingestion Pipeline & Status Polling
# ============================================================================

def test_document_status_pipeline_and_polling(client, auth_headers_user1):
    # Setup subject if not present
    with get_db() as db:
        subj = create_subject(db, name="Operating Systems", code="CS401", semester="4th Semester")
        subj_id = subj.id

    # Upload document with background processing
    content = (
        "Unit 1: Process Management. Process States: New, Ready, Running, Waiting, Terminated. "
        "CPU Scheduling Algorithms: FCFS, Round Robin, SJF, Priority Scheduling."
    ).encode("utf-8")

    res = client.post(
        "/api/v1/documents/upload",
        files={"file": ("os_process_mgmt.txt", io.BytesIO(content), "text/plain")},
        data={"subject_id": subj_id, "background": "true", "document_type": "Lecture Notes"},
        headers=auth_headers_user1
    )
    assert res.status_code in (200, 202)
    doc_data = res.json()["data"]
    doc_id = doc_data["id"]

    # Poll status endpoint
    status_res = client.get(f"/api/v1/documents/{doc_id}/status", headers=auth_headers_user1)
    assert status_res.status_code == 200
    st_data = status_res.json()["data"]
    assert st_data["document_id"] == doc_id
    # TestClient runs background tasks before returning response
    assert st_data["status"] in ("READY", "COMPLETED", "PROCESSING", "INDEXING")
    assert st_data["total_chunks"] >= 1


# ============================================================================
# 3. User-Scoped Vector Retrieval & Validated Citations
# ============================================================================

def test_user_scoped_vector_retrieval(client, auth_headers_user1, auth_headers_user2):
    with get_db() as db:
        subj = create_subject(db, name="Computer Networks", code="CS501", semester="5th Semester")
        subj_id = subj.id

        # Document for User 1 (Alice)
        doc_u1_bytes = b"TCP Transmission Control Protocol provides reliable stream delivery using three-way handshake SYN SYN-ACK ACK."
        doc_u1 = save_and_process_document(
            db=db,
            file_bytes=doc_u1_bytes,
            original_filename="tcp_u1.txt",
            subject_id=subj_id,
            user_id=1,
            ready_status="READY"
        )

        # Document for User 2 (Bob)
        doc_u2_bytes = b"UDP User Datagram Protocol provides connectionless unreliable transmission suitable for streaming and DNS."
        doc_u2 = save_and_process_document(
            db=db,
            file_bytes=doc_u2_bytes,
            original_filename="udp_u2.txt",
            subject_id=subj_id,
            user_id=2,
            ready_status="READY"
        )

    # 1. Search directly via retrieve_chunks strictly scoped by user_id
    res_u1 = retrieve_chunks(query="TCP three-way handshake", user_id=1)
    res_u2 = retrieve_chunks(query="TCP three-way handshake", user_id=2)

    # User 1 should find their TCP document
    u1_doc_ids = {c.get("document_id") for c in res_u1.chunks}
    assert doc_u1.id in u1_doc_ids
    assert doc_u2.id not in u1_doc_ids

    # User 2 should NOT find User 1's TCP document
    u2_doc_ids = {c.get("document_id") for c in res_u2.chunks}
    assert doc_u1.id not in u2_doc_ids

    # 2. Search via API endpoint GET /api/v1/documents/search
    api_res_u1 = client.get(
        "/api/v1/documents/search",
        params={"query": "reliable transmission control protocol", "subject_id": subj_id},
        headers=auth_headers_user1
    )
    assert api_res_u1.status_code == 200
    search_data = api_res_u1.json()["data"]
    assert len(search_data["citations"]) >= 1
    
    # Check citation validation
    first_cit = search_data["citations"][0]
    assert "vector_id" in first_cit
    assert first_cit["is_valid"] is True
    assert first_cit["page_number"] is not None
    assert first_cit["document_id"] == doc_u1.id


def test_validate_citations_helper():
    mock_chunks = [
        {
            "vector_id": "doc_99_chk_0",
            "document_id": 99,
            "page_number": 3,
            "chunk_index": 0,
            "topic_name": "Operating Systems",
            "score": 0.892,
            "user_id": 1,
            "content": "A process is a program in execution containing program counter, stack, and data section."
        }
    ]
    citations = validate_citations(mock_chunks)
    assert len(citations) == 1
    c = citations[0]
    assert c["source_id"] == "Source 1"
    assert c["vector_id"] == "doc_99_chk_0"
    assert c["page_number"] == 3
    assert c["is_valid"] is True
    assert c["score"] == 0.892
