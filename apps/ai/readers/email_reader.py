from pathlib import Path

from apps.ai.readers.docx_reader import read_docx
from apps.ai.readers.pdf_reader import read_pdf


def read_email_attachment(file_path: str | Path) -> str:
    """
    Read supported email attachment.

    Supported:
    - PDF
    - DOCX
    """

    extension = Path(file_path).suffix.lower()

    if extension == ".pdf":
        return read_pdf(file_path)

    if extension == ".docx":
        return read_docx(file_path)

    raise ValueError(f"Unsupported attachment type: {extension}")
