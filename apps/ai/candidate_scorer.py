from openai import OpenAI

from apps.ai.clients.openai_client import get_openai_client
from apps.ai.config import get_settings
from apps.ai.models.candidate import CandidateProfile
from apps.ai.models.job import JobDescription
from apps.ai.models.score import CandidateScore
from apps.ai.prompts_loader import load_prompt


class CandidateScorer:
    """
    AI Candidate Scorer.
    """

    def __init__(self) -> None:
        self.client: OpenAI = get_openai_client()
        self.settings = get_settings()

        self.system_prompt = load_prompt(
            "scorer_prompt.txt"
        )

    def score_candidate(
        self,
        candidate: CandidateProfile,
        job: JobDescription,
    ) -> CandidateScore:
        """
        Compare candidate against job description.

        Args:
            candidate: Parsed candidate profile.
            job: Parsed job description.

        Returns:
            CandidateScore
        """

        candidate_json = candidate.model_dump_json(indent=2)

        job_json = job.model_dump_json(indent=2)

        user_prompt = f"""
Candidate Profile

{candidate_json}

----------------------------------------

Job Description

{job_json}
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
            text_format=CandidateScore,
        )

        return response.output_parsed
