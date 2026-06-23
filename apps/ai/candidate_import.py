"""
Candidate import module.

Routes every supported candidate source
to the correct reader.
"""

from pathlib import Path
from typing import Any

import pandas as pd

from apps.ai.readers.bullhorn_reader import read_bullhorn_export
from apps.ai.readers.csv_reader import read_csv
from apps.ai.readers.docx_reader import read_docx
from apps.ai.readers.email_reader import read_email_attachment
from apps.ai.readers.linkedin_reader import read_linkedin_profile
from apps.ai.readers.pdf_reader import read_pdf
from apps.ai.readers.recruitcrm_reader import read_recruitcrm_export


def import_candidate(
    file_path: str | Path,
    source: str,
) -> str | pd.DataFrame:
    """
    Import candidate from supported sources.

    Supported Sources:
        - pdf
        - docx
        - csv
        - recruitcrm
        - bullhorn
        - linkedin
        - email

    Returns:
        str | pd.DataFrame
    """

    source = source.lower()

    if source == "pdf":
        return read_pdf(file_path)

    if source == "docx":
        return read_docx(file_path)

    if source == "csv":
        return read_csv(file_path)

    if source == "recruitcrm":
        return read_recruitcrm_export(file_path)

    if source == "bullhorn":
        return read_bullhorn_export(file_path)

    if source == "linkedin":
        return read_linkedin_profile(file_path)

    if source == "email":
        return read_email_attachment(file_path)

    raise ValueError(
        f"Unsupported candidate source: {source}"
    )


def import_manual_candidate(
    candidate_data: dict[str, Any],
) -> dict[str, Any]:
    """
    Manual candidate entry.

    Returns:
        dict
    """

    return candidate_data
