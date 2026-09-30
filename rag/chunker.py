from typing import List, Dict, Any
from rag.text_cleaner import clean_text

def recursive_split_text(
    text: str,
    chunk_size: int = 600,
    chunk_overlap: int = 80,
    separators: List[str] = None
) -> List[str]:
    """
    Recursively splits text into chunks under chunk_size while respecting natural boundaries.
    """
    if separators is None:
        separators = ["\n\n", "\n", ". ", "; ", ", ", " ", ""]

    if len(text) <= chunk_size:
        return [text] if text.strip() else []

    # Find the first separator that appears in text
    chosen_sep = separators[-1]
    for sep in separators:
        if sep and sep in text:
            chosen_sep = sep
            break

    splits = text.split(chosen_sep) if chosen_sep else list(text)

    chunks = []
    current_chunk = ""

    for part in splits:
        candidate = f"{current_chunk}{chosen_sep}{part}" if current_chunk else part
        if len(candidate) <= chunk_size:
            current_chunk = candidate
        else:
            if current_chunk.strip():
                chunks.append(current_chunk.strip())
            # If a single part exceeds chunk_size on its own, recurse with finer separators
            if len(part) > chunk_size and len(separators) > 1:
                sub_chunks = recursive_split_text(
                    part,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap,
                    separators=separators[separators.index(chosen_sep) + 1:]
                )
                chunks.extend(sub_chunks)
                current_chunk = ""
            else:
                # Add overlap from the end of the previous chunk if available
                if chunk_overlap > 0 and len(current_chunk) > chunk_overlap:
                    overlap_prefix = current_chunk[-chunk_overlap:]
                    current_chunk = f"{overlap_prefix}{chosen_sep}{part}"
                else:
                    current_chunk = part

    if current_chunk.strip():
        chunks.append(current_chunk.strip())

    return [c for c in chunks if c.strip()]


def chunk_document_pages(
    pages: List[Dict[str, Any]],
    chunk_size: int = 600,
    chunk_overlap: int = 80
) -> List[Dict[str, Any]]:
    """
    Takes extracted pages and produces structured, page-aware chunks.

    Args:
        pages: List of {"page_number": int, "text": str}
        chunk_size: Target maximum characters per chunk.
        chunk_overlap: Overlap between consecutive chunks.

    Returns:
        List of dicts:
        [
            {
                "chunk_index": 0,
                "page_number": 1,
                "content": "...",
                "char_count": 450
            },
            ...
        ]
    """
    all_chunks = []
    global_index = 0

    for page in pages:
        page_num = page.get("page_number", 1)
        raw_text = page.get("text", "")
        cleaned = clean_text(raw_text)

        if not cleaned:
            continue

        page_chunks = recursive_split_text(
            text=cleaned,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap
        )

        for chunk_text in page_chunks:
            all_chunks.append({
                "chunk_index": global_index,
                "page_number": page_num,
                "content": chunk_text,
                "char_count": len(chunk_text)
            })
            global_index += 1

    return all_chunks
