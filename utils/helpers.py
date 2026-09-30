import re
from datetime import datetime
from typing import Optional

def format_datetime(dt: Optional[datetime], fmt: str = "%b %d, %Y %I:%M %p") -> str:
    """Formats a datetime object nicely."""
    if not dt:
        return "N/A"
    return dt.strftime(fmt)

def sanitize_filename(name: str) -> str:
    """Sanitizes an uploaded file name to avoid path traversal and unsafe characters."""
    clean = re.sub(r'[^a-zA-Z0-9_.-]', '_', name)
    return clean.strip('._')

def format_file_size(size_bytes: int) -> str:
    """Formats bytes into human readable KB / MB."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
