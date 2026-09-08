import logging
from openai import OpenAI

from apps.ai.clients.openai_client import get_openai_client
from apps.ai.config import get_settings
from apps.ai.models.weights import JobScoreWeights
from apps.ai.prompts_loader import load_prompt

logger = logging.getLogger(__name__)


class JobWeightsAnalyzer:
    """
    AI analyzer that evaluates job criteria and determines priority weights
    for candidate scoring dimensions.
    """

    def __init__(self) -> None:
        self.client: OpenAI = get_openai_client()
        self.settings = get_settings()
        self.system_prompt = load_prompt("job_weights_prompt.txt")

    def evaluate_weights(
        self,
        job_title: str,
        description: str,
        skills: list = None,
        location: str = None,
        experience_required: int = 0,
        job_type: str = None,
        salary_range: str = None,
    ) -> JobScoreWeights:
        """
        Analyze job details to derive priority weights for scoring dimensions.
        """
        skills_str = ", ".join(skills) if isinstance(skills, list) else (skills or "None specified")
        user_prompt = f"""Job Title: {job_title or 'Not specified'}
Job Type: {job_type or 'Not specified'}
Location: {location or 'Not specified'}
Experience Required: {experience_required or 0} years
Salary Range: {salary_range or 'Not specified'}
Required / Key Skills: {skills_str}

Job Description:
{description or job_title or 'None specified'}
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
                    "content": user_prompt,
                },
            ],
            text_format=JobScoreWeights,
        )

        return response.output_parsed
