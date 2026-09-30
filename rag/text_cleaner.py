import re
import unicodedata

def clean_text(raw_text: str) -> str:
    """
    Cleans and normalizes extracted academic text.

    Operations:
    1. Normalizes unicode characters (NFKC).
    2. Replaces carriage returns and non-breaking spaces.
    3. Merges hyphenated words broken across lines (e.g. 'multi-\nagent' -> 'multi-agent').
    4. Collapses excessive whitespace and empty lines.
    5. Strips control characters while preserving formatting and symbols.
    """
    if not raw_text:
        return ""

    # Normalize unicode
    text = unicodedata.normalize("NFKC", raw_text)

    # Standardize line endings and replace tabs/non-breaking spaces
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = text.replace("\u00a0", " ").replace("\t", "    ")

    # Fix broken hyphenated words at line breaks (e.g. 'com-\nputer' -> 'computer')
    text = re.sub(r'(\b[a-zA-Z]{2,})-\n([a-zA-Z]{2,}\b)', r'\1\2', text)

    # Remove non-printable control characters except newline
    text = "".join(ch for ch in text if ch == "\n" or unicodedata.category(ch)[0] != "C")

    # Collapse multiple consecutive horizontal spaces into one
    text = re.sub(r'[^\S\n]+', ' ', text)

    # Collapse more than two consecutive newlines into two
    text = re.sub(r'\n{3,}', '\n\n', text)

    return text.strip()
