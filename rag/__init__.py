"""RAG processing package for AI Student Copilot."""
from rag.document_loader import extract_text_from_pdf
from rag.text_cleaner import clean_text
from rag.chunker import chunk_document_pages
from rag.embeddings import get_embedding_generator
from rag.vector_store import get_vector_store

__all__ = [
    "extract_text_from_pdf",
    "clean_text",
    "chunk_document_pages",
    "get_embedding_generator",
    "get_vector_store",
]
