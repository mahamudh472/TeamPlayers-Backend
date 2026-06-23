"""
Job description models.

These models represent a parsed job description used for
AI candidate matching and scoring.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class JobRequirement(BaseModel):
    """
    Individual job requirement.
    """

    name: str
    required: bool = True


class JobDescription(BaseModel):
    """
    Parsed job description.
    """

    # Basic Information

    job_title: str = ""

    company_name: Optional[str] = None

    department: Optional[str] = None

    industry: Optional[str] = None

    employment_type: Optional[str] = None

    work_mode: Optional[str] = None

    location: Optional[str] = None

    # Experience

    minimum_experience: Optional[float] = None

    maximum_experience: Optional[float] = None

    # Salary

    minimum_salary: Optional[str] = None

    maximum_salary: Optional[str] = None

    currency: Optional[str] = None

    # Skills

    required_skills: List[str] = Field(default_factory=list)

    preferred_skills: List[str] = Field(default_factory=list)

    required_languages: List[str] = Field(default_factory=list)

    required_certifications: List[str] = Field(default_factory=list)

    # Education

    required_degree: Optional[str] = None

    preferred_degree: Optional[str] = None

    # Responsibilities

    responsibilities: List[str] = Field(default_factory=list)

    requirements: List[JobRequirement] = Field(default_factory=list)

    benefits: List[str] = Field(default_factory=list)

    # AI Metadata

    raw_text: Optional[str] = None

    parsing_confidence: Optional[float] = None
