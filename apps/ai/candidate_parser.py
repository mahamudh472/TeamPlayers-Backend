from openai import OpenAI

from apps.ai.clients.openai_client import get_openai_client
from apps.ai.config import get_settings
from apps.ai.models.candidate import CandidateProfile
from apps.ai.prompts_loader import load_prompt


class CandidateParser:
    """
    AI Candidate Parser.
    """

    def __init__(self) -> None:

        self.client: OpenAI = get_openai_client()

        self.settings = get_settings()

        self.system_prompt = load_prompt(
            "parser_prompt.txt"
        )

    def parse_candidate(
        self,
        resume_text: str,
    ) -> CandidateProfile:
        """
        Parse candidate resume.

        Args:
            resume_text: Resume text.

        Returns:
            CandidateProfile
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
                    "content": resume_text,
                },
            ],
            text_format=CandidateProfile,
        )

        return response.output_parsed
