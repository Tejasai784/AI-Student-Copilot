"""Document Reader Tool.
Enables agents to inspect uploaded academic files, examine sections, and read content.
"""
from __future__ import annotations

from typing import Dict, Any, Optional
from pathlib import Path
from tools.registry import BaseTool
from database.database import get_db
from database.crud import get_document_by_id, get_document_chunks, get_documents


from tools.schemas import DocumentReaderInput


class DocumentReaderTool(BaseTool):
    name = "document_reader"
    description = "Reads text and page segments from uploaded academic documents (PDF, DOCX, TXT, CSV)."
    args_model = DocumentReaderInput
    parameters_schema = {
        "type": "object",
        "properties": {
            "document_id": {
                "type": "integer",
                "description": "The ID of the document to inspect."
            },
            "page_number": {
                "type": "integer",
                "description": "Optional specific page number to retrieve."
            }
        },
        "required": ["document_id"]
    }

    def execute(self, document_id: int, page_number: Optional[int] = None, **kwargs) -> Dict[str, Any]:
        with get_db() as db:
            doc = get_document_by_id(db, document_id)
            if not doc:
                # Fallback: check if any document exists
                all_docs = get_documents(db)
                if all_docs:
                    doc = all_docs[0]
                else:
                    return {"ok": False, "error": f"No document found with ID {document_id}."}

            chunks = get_document_chunks(db, doc.id)
            if page_number is not None:
                filtered = [c for c in chunks if c.page_number == page_number]
                if not filtered:
                    return {
                        "ok": False,
                        "error": f"Page {page_number} not found in document '{doc.filename}' (total pages: {doc.total_pages})."
                    }
                content = "\n\n".join(f"[Page {c.page_number}] {c.content}" for c in filtered)
            else:
                # Return first 5 chunks if no page specified
                content = "\n\n".join(f"[Page {c.page_number}] {c.content}" for c in chunks[:5])

            return {
                "ok": True,
                "document_id": doc.id,
                "filename": doc.filename,
                "total_pages": doc.total_pages,
                "total_chunks": doc.total_chunks,
                "content": content
            }
