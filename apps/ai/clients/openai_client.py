"""
OpenAI client.

This module creates and returns a reusable OpenAI client
for the entire application.
"""

from functools import lru_cache

from openai import OpenAI

from apps.ai.config import get_settings


@lru_cache
def get_openai_client() -> OpenAI:
    """
    Create and return a reusable OpenAI client.

    Returns:
        OpenAI: Configured OpenAI client.
    """

    settings = get_settings()

    return OpenAI(
        api_key=settings.openai_api_key
    )
