"""
Job score weight models.

These models represent the relative priority/weight of each scoring dimension
(skills, experience, salary, location, certification) for calculating
a candidate's overall match score against a job.
"""

from pydantic import BaseModel, Field


class JobScoreWeights(BaseModel):
    """
    Priority weights for candidate scoring dimensions (values summing to 100).
    """

    skills_weight: float = Field(
        default=20.0,
        ge=0,
        le=100,
        description="Weight for skills match evaluation (0-100)."
    )

    experience_weight: float = Field(
        default=20.0,
        ge=0,
        le=100,
        description="Weight for experience match evaluation (0-100)."
    )

    salary_weight: float = Field(
        default=20.0,
        ge=0,
        le=100,
        description="Weight for salary alignment evaluation (0-100)."
    )

    location_weight: float = Field(
        default=20.0,
        ge=0,
        le=100,
        description="Weight for location fit evaluation (0-100)."
    )

    certification_weight: float = Field(
        default=20.0,
        ge=0,
        le=100,
        description="Weight for certification match evaluation (0-100)."
    )
