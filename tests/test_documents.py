import pytest
from tests.pdf_test_utils import generate_minimal_pdf
from rag.document_loader import extract_text_from_pdf, PDFExtractionError
from rag.text_cleaner import clean_text
from rag.chunker import chunk_document_pages, recursive_split_text
from services.document_service import validate_pdf_file
from utils.helpers import sanitize_filename

def test_validate_pdf_file():
    valid_bytes = generate_minimal_pdf(["Unit 1: Introduction to Operating Systems"])
    
    # Valid PDF
    is_valid, err = validate_pdf_file(valid_bytes, "lecture_notes.pdf")
    assert is_valid is True
    assert err == ""

    # Invalid extension
    is_valid, err = validate_pdf_file(valid_bytes, "lecture_notes.docx")
    assert is_valid is False
    assert "Only PDF" in err

    # Empty file
    is_valid, err = validate_pdf_file(b"", "empty.pdf")
    assert is_valid is False
    assert "empty" in err.lower()

    # Oversized file (>25MB limit)
    fake_large_bytes = b"%PDF-" + b"0" * (26 * 1024 * 1024)
    is_valid, err = validate_pdf_file(fake_large_bytes, "large.pdf", max_size_mb=25)
    assert is_valid is False
    assert "exceeds" in err.lower()

    # Corrupt / invalid magic bytes
    is_valid, err = validate_pdf_file(b"NOT_A_PDF_CONTENT", "fake.pdf")
    assert is_valid is False
    assert "Invalid PDF header" in err

def test_filename_sanitization():
    unsafe_names = [
        ("../../etc/passwd.pdf", "etc_passwd.pdf"),
        ("notes (unit 1) & test!@#.pdf", "notes__unit_1____test___.pdf"),
        ("C:\\Windows\\System32\\notes.pdf", "C__Windows_System32_notes.pdf"),
    ]
    for unsafe, expected in unsafe_names:
        sanitized = sanitize_filename(unsafe)
        assert "/" not in sanitized
        assert ".." not in sanitized

def test_pdf_text_extraction_and_page_tracking():
    pages_content = [
        "Page One: Relational Databases and SQL.",
        "Page Two: Normalization up to Boyce-Codd Normal Form (BCNF).",
        "Page Three: Transaction ACID Properties and Concurrency."
    ]
    pdf_bytes = generate_minimal_pdf(pages_content)
    extracted = extract_text_from_pdf(pdf_bytes)

    assert len(extracted) == 3
    assert extracted[0]["page_number"] == 1
    assert "Relational Databases" in extracted[0]["text"]
    assert extracted[1]["page_number"] == 2
    assert "Boyce-Codd" in extracted[1]["text"]
    assert extracted[2]["page_number"] == 3
    assert "ACID" in extracted[2]["text"]

def test_text_cleaner():
    raw = "Multi-\nagent system with \r\n multiple   spaces\tand\u00a0non-breaking.\n\n\n\nNew paragraph."
    cleaned = clean_text(raw)
    assert "Multiagent system" in cleaned
    assert "multiple spaces and non-breaking." in cleaned
    assert "\n\n\n" not in cleaned
    assert "New paragraph." in cleaned

def test_chunker_page_tracking_and_boundaries():
    pages = [
        {
            "page_number": 1,
            "text": "Intro to Operating Systems.\nProcess Management.\nCPU Scheduling."
        },
        {
            "page_number": 2,
            "text": "Deadlock Detection and Banker's Algorithm.\nMemory Paging and Segmentation."
        }
    ]
    chunks = chunk_document_pages(pages, chunk_size=50, chunk_overlap=10)
    assert len(chunks) >= 2
    
    # Check that each chunk has page number and chunk index
    for idx, chk in enumerate(chunks):
        assert chk["chunk_index"] == idx
        assert chk["page_number"] in [1, 2]
        assert len(chk["content"]) > 0
        assert chk["char_count"] == len(chk["content"])
