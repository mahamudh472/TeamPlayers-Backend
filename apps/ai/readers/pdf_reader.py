from pathlib import Path

import fitz


def read_pdf(file_path: str | Path) -> str:
    """
    Read PDF and return extracted text.
    """

    document = fitz.open(file_path)

    text = ""

    for page in document:
        text += page.get_text()

    document.close()

    return text.strip()
