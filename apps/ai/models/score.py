"""
AI candidate scoring models.

These models represent the AI evaluation of a candidate
against a specific job description.
"""

from pydantic import BaseModel, Field


class MatchDetail(BaseModel):
    matched: bool = False
    score: float = Field(default=0, ge=0, le=100)
    reason: str = ""


class CandidateScore(BaseModel):
    skills_match: MatchDetail = Field(default_factory=MatchDetail)

    experience_match: MatchDetail = Field(default_factory=MatchDetail)

    salary_alignment: MatchDetail = Field(default_factory=MatchDetail)

    location_alignment: MatchDetail = Field(default_factory=MatchDetail)
