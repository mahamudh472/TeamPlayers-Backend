"""
Company Parser.

Uses OpenAI structured outputs to extract and validate authentic corporate lead profiles
from raw search result snippets and directories.
"""

import logging
from typing import Optional
from openai import OpenAI

from apps.ai.clients.openai_client import get_openai_client
from apps.ai.config import get_settings
from apps.ai.models.company import CompanyLeadProfile
from apps.ai.prompts_loader import load_prompt

logger = logging.getLogger(__name__)


class CompanyParser:
    """
    AI Company Lead Parser.
    """

    def __init__(self) -> None:
        self.client: OpenAI = get_openai_client()
        self.settings = get_settings()
        self.system_prompt = load_prompt("company_parser_prompt.txt")

    def parse_company(self, search_text: str) -> Optional[CompanyLeadProfile]:
        """
        Parse raw search result or scraped text into a verified CompanyLeadProfile.

        Args:
            search_text: Text snippet containing title, URL, snippet, and default parameters.

        Returns:
            CompanyLeadProfile or None if parsing fails.
        """
        try:
            response = self.client.responses.parse(
                model=self.settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": self.system_prompt,
                    },
                    {
                        "role": "user",
                        "content": search_text,
                    },
                ],
                text_format=CompanyLeadProfile,
            )
            return response.output_parsed
        except Exception as e:
            logger.error(f"[CompanyParser] Failed to parse company profile via OpenAI: {e}")
            return None
