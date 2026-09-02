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

        try:
            self.system_prompt = load_prompt("job_parser_prompt.txt")
        except Exception:
            self.system_prompt = load_prompt("parser_prompt.txt")

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
        import logging
        logger = logging.getLogger(__name__)

        if not job_description or not job_description.strip():
            return JobDescription(raw_text=job_description or "")

        try:
            # Truncate overly long text to prevent model max output tokens truncation
            cleaned_text = job_description[:6000]

            response = self.client.responses.parse(
                model=self.settings.openai_model,
                input=[
                    {
                        "role": "system",
                        "content": self.system_prompt,
                    },
                    {
                        "role": "user",
                        "content": cleaned_text,
                    },
                ],
                text_format=JobDescription,
            )

            result = response.output_parsed
            if result:
                result.raw_text = job_description
            return result
        except Exception as e:
            logger.error(f"Failed to parse job description via OpenAI: {e}")
            return JobDescription(
                raw_text=job_description[:4000]
            )
