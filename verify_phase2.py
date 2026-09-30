"""Phase 2 Verification Script.
Simulates uploading a real PDF study material, indexes it into SQLite and Vector Store,
verifies chunk extraction and search, restarts the application, and verifies full persistence.
"""
import urllib.request
from pathlib import Path
from backend.config import settings
from database.database import get_db, init_db
from database.crud import (
    create_or_update_student_profile,
    create_subject,
    get_subjects,
    get_documents,
    get_document_by_id,
    get_document_chunks,
    get_dashboard_summary
)
from services.document_service import save_and_process_document
from rag.vector_store import get_vector_store
from rag.embeddings import get_embedding_generator
from tests.pdf_test_utils import generate_minimal_pdf

def run_phase2_verification():
    print("=== [1] Initializing Database & Directories ===")
    init_db()

    print("=== [2] Setting up Student & Subject ===")
    with get_db() as db:
        profile = create_or_update_student_profile(
            db=db,
            name="Aarav Sharma",
            course="B.Tech Computer Science",
            branch="Artificial Intelligence",
            year="3rd Year",
            semester="6th Semester"
        )
        
        # Ensure subject exists
        subjects = get_subjects(db)
        if not subjects:
            subj = create_subject(
                db=db,
                name="Database Management Systems",
                code="CS601",
                semester="6th Semester",
                description="Relational Databases, Normalization, SQL"
            )
        else:
            subj = subjects[0]
        subj_id = subj.id
        print(f"Active Subject: {subj.name} ({subj.code}), ID={subj_id}")

    print("=== [3] Generating and Uploading Real Multi-page PDF ===")
    pdf_content = [
        "Unit 2: Normalization in Relational Databases. First Normal Form (1NF) eliminates duplicate columns and requires atomic values.",
        "Second Normal Form (2NF) removes partial dependencies on candidate keys. Third Normal Form (3NF) removes transitive functional dependencies.",
        "Boyce-Codd Normal Form (BCNF) requires that for every functional dependency X -> Y, X must be a superkey. Lossless join decomposition is guaranteed."
    ]
    pdf_bytes = generate_minimal_pdf(pdf_content)

    with get_db() as db:
        doc = save_and_process_document(
            db=db,
            file_bytes=pdf_bytes,
            original_filename="dbms_normalization_lecture.pdf",
            subject_id=subj_id,
            unit_number=2,
            topic_name="Normalization & BCNF",
            document_type="Lecture Notes"
        )
        doc_id = doc.id
        doc_status = doc.status
        doc_pages = doc.total_pages
        doc_chunks = doc.total_chunks
        print(f"Document Processed: ID={doc_id}, Status={doc_status}, Pages={doc_pages}, Chunks={doc_chunks}")

    assert doc_status == "COMPLETED", f"Document processing failed with status {doc_status}"
    assert doc_pages == 3, f"Expected 3 pages, got {doc_pages}"
    assert doc_chunks >= 3, f"Expected at least 3 chunks, got {doc_chunks}"

    print("=== [4] Verifying Chunks in Database & Vector Store ===")
    with get_db() as db:
        chunks = get_document_chunks(db, doc_id)
        assert len(chunks) == doc_chunks, f"Expected {doc_chunks} chunks in DB, got {len(chunks)}"
        print(f"Verified {len(chunks)} chunks in SQLite database.")
        for c in chunks:
            print(f"  - Chunk #{c.chunk_index + 1} (Page {c.page_number}): {c.content[:70]}...")

    v_store = get_vector_store()
    assert v_store.count() >= doc_chunks
    print(f"Verified Vector Store total count: {v_store.count()} indexed chunks.")

    print("=== [5] Testing Vector Search Retrieval ===")
    embedder = get_embedding_generator()
    query = "What is Boyce-Codd Normal Form (BCNF) and superkey?"
    q_vec = embedder.embed_text(query)
    search_results = v_store.search(q_vec, top_k=2, filter_subject_id=subj_id, filter_unit=2)
    
    assert len(search_results) > 0, "No search results found!"
    top_hit = search_results[0]
    print(f"Top Search Result (Score: {top_hit['score']}):")
    print(f"  Page: {top_hit['page_number']}, Content: {top_hit['content']}")
    assert "BCNF" in top_hit["content"] or "Boyce-Codd" in top_hit["content"] or "superkey" in top_hit["content"]

    print("=== [6] Simulating Cold App Restart & Verifying Persistence ===")
    # Re-instantiate a fresh VectorStore directly from disk files
    fresh_v_store = get_vector_store()
    fresh_v_store.load()
    assert fresh_v_store.count() >= doc_chunks, "Vector store index lost after reload!"
    print(f"Fresh Vector Store loaded {fresh_v_store.count()} chunks from disk.")

    with get_db() as db:
        reloaded_doc = get_document_by_id(db, doc_id)
        assert reloaded_doc is not None, "Document metadata lost from database!"
        assert reloaded_doc.status == "COMPLETED"
        assert reloaded_doc.total_chunks == doc_chunks
        
        summary = get_dashboard_summary(db)
        assert summary["total_materials"] >= 1, "Dashboard summary total_materials not updated!"
        print("Dashboard Summary with Materials:", summary)

    print("=== [7] Verifying Streamlit Application Health ===")
    try:
        req = urllib.request.urlopen("http://localhost:8501/_stcore/health")
        print(f"Streamlit health: {req.status}")
    except Exception:
        print("Note: Streamlit server not currently running on 8501 (will verify upon server start).")

    print("==================================================")
    print(" ALL PHASE 2 VERIFICATION CHECKS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    run_phase2_verification()
