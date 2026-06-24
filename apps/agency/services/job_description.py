"""
Job description generation service.

Handles document reading, text combining, and AI generation.
"""

import logging
import uuid
from pathlib import Path

from django.core.files.uploadedfile import UploadedFile
from rest_framework.exceptions import ValidationError

from apps.ai.job_description_generator import JobDescriptionGenerator
from apps.ai.readers.docx_reader import read_docx
from apps.ai.readers.pdf_reader import read_pdf

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".txt"}
TEMP_DIR = Path("temp/job_descriptions")


def _save_temp_file(document: UploadedFile) -> Path:
    """
    Save uploaded file to a temporary location and return the path.
    """

    TEMP_DIR.mkdir(parents=True, exist_ok=True)

    extension = Path(document.name).suffix.lower()
    file_name = f"{uuid.uuid4().hex}{extension}"
    file_path = TEMP_DIR / file_name

    with open(file_path, "wb") as f:
        for chunk in document.chunks():
            f.write(chunk)

    return file_path


def _extract_text_from_file(file_path: Path) -> str:
    """
    Extract text from a file based on its extension.
    """

    extension = file_path.suffix.lower()

    if extension == ".pdf":
        return read_pdf(file_path)

    if extension == ".docx":
        return read_docx(file_path)

    if extension == ".txt":
        return file_path.read_text(encoding="utf-8").strip()

    raise ValidationError(
        f"Unsupported file type: {extension}. "
        f"Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
    )


def _cleanup_temp_file(file_path: Path) -> None:
    """
    Remove temporary file if it exists.
    """

    if file_path and file_path.exists():
        file_path.unlink()


def generate_job_description(
    document: UploadedFile | None = None,
    text: str | None = None,
) -> dict:
    """
    Generate a job description from a document and/or text.

    Args:
        document: Uploaded file (PDF, DOCX, or TXT). Optional.
        text: Freeform text input. Optional.

    Returns:
        dict with the AI generation result.

    Raises:
        ValidationError: When no input is provided or file type is unsupported.
    """

    if not document and not text:
        raise ValidationError(
            "At least one of 'document' or 'text' must be provided."
        )

    # Validate file extension early
    if document:
        extension = Path(document.name).suffix.lower()
        if extension not in SUPPORTED_EXTENSIONS:
            raise ValidationError(
                f"Unsupported file type: {extension}. "
                f"Supported types: {', '.join(SUPPORTED_EXTENSIONS)}"
            )

    combined_parts = []
    temp_path = None

    try:
        # Extract text from document
        if document:
            temp_path = _save_temp_file(document)
            document_text = _extract_text_from_file(temp_path)
            if document_text:
                combined_parts.append(document_text)

        # Append freeform text
        if text and text.strip():
            combined_parts.append(text.strip())

        if not combined_parts:
            raise ValidationError(
                "No readable content found in the provided input."
            )

        combined_text = "\n\n".join(combined_parts)

        # Generate via AI
        generator = JobDescriptionGenerator()
        result = generator.generate(combined_text)

        return result.model_dump()

    except ValidationError:
        raise

    except Exception:
        logger.exception("AI job description generation failed")
        raise ValidationError(
            "An unexpected error occurred while generating "
            "the job description. Please try again."
        )

    finally:
        if temp_path:
            _cleanup_temp_file(temp_path)
