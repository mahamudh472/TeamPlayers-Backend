from pathlib import Path

from apps.ai.readers.pdf_reader import read_pdf


def read_linkedin_profile(file_path: str | Path) -> str:
    """
    Read exported LinkedIn PDF profile.
    """

    return read_pdf(file_path)
