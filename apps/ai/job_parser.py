from openai import OpenAI

from apps.ai.clients.openai_client import get_openai_client
from apps.ai.config import get_settings
from apps.ai.models.job import JobDescription
from apps.ai.prompts_loader import load_prompt


class JobParser:
    """
    Parse job descriptions using OpenAI.
    """

    def __init__(self) -> None:
        self.client: OpenAI = get_openai_client()
        self.settings = get_settings()

        self.system_prompt = load_prompt(
            "parser_prompt.txt"
        )

    def parse_job_description(
        self,
        job_description: str,
    ) -> JobDescription:
        """
        Parse job description.

        Args:
            job_description: Job description text.

        Returns:
            JobDescription
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
                    "content": job_description,
                },
            ],
            text_format=JobDescription,
        )

        return response.output_parsed
