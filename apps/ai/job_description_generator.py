"""
Job description generator using OpenAI.

Accepts raw text and returns a structured job description
or an error when the input is unrelated.
"""

from openai import OpenAI

from apps.ai.clients.openai_client import get_openai_client
from apps.ai.config import get_settings
from apps.ai.models.job_description_result import GeneratedJobDescription
from apps.ai.prompts_loader import load_prompt


class JobDescriptionGenerator:
    """
    Generate structured job descriptions using OpenAI.
    """

    def __init__(self) -> None:
        self.client: OpenAI = get_openai_client()
        self.settings = get_settings()
        self.system_prompt = load_prompt(
            "job_description_generator_prompt.txt"
        )

    def generate(self, text: str) -> GeneratedJobDescription:
        """
        Generate a job description from input text.

        Args:
            text: Combined document and/or freeform text.

        Returns:
            GeneratedJobDescription with success/error status.
        """

        response = self.client.responses.parse(
            model=self.settings.openai_model,
            input=[
                {
                    "role": "system",
                    "content": self.system_prompt,
                },
                {
                    "role": "user",
                    "content": text,
                },
            ],
            text_format=GeneratedJobDescription,
        )

        return response.output_parsed
