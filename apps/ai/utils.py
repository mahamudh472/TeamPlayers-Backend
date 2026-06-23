from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path
from typing import Any


def create_directory(directory: str | Path) -> Path:
    """
    Create directory if it does not exist.
    """

    path = Path(directory)
    path.mkdir(parents=True, exist_ok=True)
    return path


def save_uploaded_file(
    uploaded_file: Any,
    save_directory: str | Path,
) -> Path:
    """
    Save uploaded file and return file path.
    """

    create_directory(save_directory)

    extension = Path(uploaded_file.name).suffix

    file_name = f"{uuid.uuid4().hex}{extension}"

    file_path = Path(save_directory) / file_name

    with open(file_path, "wb") as file:
        file.write(uploaded_file.getbuffer())

    return file_path


def remove_file(file_path: str | Path) -> None:
    """
    Remove a file.
    """

    path = Path(file_path)

    if path.exists():
        path.unlink()


def remove_directory(directory: str | Path) -> None:
    """
    Remove a directory.
    """

    path = Path(directory)

    if path.exists():
        shutil.rmtree(path)


def load_json(file_path: str | Path) -> dict:
    """
    Load JSON file.
    """

    with open(file_path, "r", encoding="utf-8") as file:
        return json.load(file)


def save_json(
    data: dict,
    file_path: str | Path,
) -> None:
    """
    Save JSON file.
    """

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            indent=4,
            ensure_ascii=False,
        )


def get_file_extension(file_path: str | Path) -> str:
    """
    Return file extension.
    """

    return Path(file_path).suffix.lower()


def file_exists(file_path: str | Path) -> bool:
    """
    Check file exists.
    """

    return Path(file_path).exists()
