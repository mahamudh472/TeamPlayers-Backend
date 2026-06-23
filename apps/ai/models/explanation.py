"""
AI explanation models.

These models provide transparent reasoning behind
the AI candidate scoring results.
"""

from typing import List

from pydantic import BaseModel, Field


class ExplanationItem(BaseModel):
    """
    Represents one explanation section.
    """

    title: str

    matched: bool

    score: float = Field(
        ge=0,
        le=100
    )

    reason: str


class AIExplanation(BaseModel):
    """
    Detailed AI explanation returned to recruiters.
    """

    skills_match: ExplanationItem

    experience_match: ExplanationItem

    salary_alignment: ExplanationItem

    location_alignment: ExplanationItem

    key_strengths: List[str] = Field(default_factory=list)

    missing_requirements: List[str] = Field(default_factory=list)

    red_flags: List[str] = Field(default_factory=list)

    recruiter_summary: str

    recommended_action: str

    overall_reasoning: str
