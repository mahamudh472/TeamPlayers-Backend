from pathlib import Path

from docx import Document


def read_docx(file_path: str | Path) -> str:
    """
    Read DOCX and return extracted text.
    """

    document = Document(file_path)

    text = "\n".join(
        paragraph.text
        for paragraph in document.paragraphs
    )

    return text.strip()
