from openai import OpenAI

from apps.ai.clients.openai_client import get_openai_client
from apps.ai.config import get_settings
from apps.ai.models.explanation import AIExplanation
from apps.ai.models.score import CandidateScore
from apps.ai.prompts_loader import load_prompt


class CandidateExplainer:
    """
    Generate AI explanation for a candidate score.
    """

    def __init__(self) -> None:
        self.client: OpenAI = get_openai_client()
        self.settings = get_settings()

        self.system_prompt = load_prompt(
            "explanation_prompt.txt"
        )

    def generate_explanation(
        self,
        score: CandidateScore,
    ) -> AIExplanation:
        """
        Generate AI explanation.

        Args:
            score: CandidateScore

        Returns:
            AIExplanation
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
                    "content": score.model_dump_json(indent=2),
                },
            ],
            text_format=AIExplanation,
        )

        return response.output_parsed
