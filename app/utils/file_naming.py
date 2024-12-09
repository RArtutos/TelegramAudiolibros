import os
import re

def sanitize_filename(title: str) -> str:
    """Sanitize the title to create a valid filename."""
    # Remove special characters but keep spaces, hyphens and underscores
    safe_title = "".join(x for x in title if x.isalnum() or x in (' ', '-', '_')).strip()
    return safe_title

def get_audiobook_filename(title: str, part: int = None, total_parts: int = None) -> str:
    """Generate a filename for the audiobook with @Artutos suffix."""
    safe_title = sanitize_filename(title)
    if part is not None and total_parts is not None:
        return f"{safe_title} @Artutos (Parte {part} de {total_parts}).mp3"
    return f"{safe_title} @Artutos.mp3"