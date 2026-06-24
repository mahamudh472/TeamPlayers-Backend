"""
Job description generation result model.

Used by the AI to return a structured job description
or an error when the input is unrelated/unprocessable.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class GeneratedJobDescription(BaseModel):
    """
    AI-generated structured job description with success/error handling.
    """

    # Status

    success: bool = Field(
        description="True if a valid job description was generated, "
        "False if the input was unrelated or unprocessable."
    )

    error_message: Optional[str] = Field(
        default=None,
        description="Human-readable error when success is False.",
    )

    # Basic Information

    job_title: Optional[str] = None

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

    # Content

    summary: Optional[str] = Field(
        default=None,
        description="A concise 2-3 sentence overview of the role.",
    )

    responsibilities: List[str] = Field(default_factory=list)

    requirements: List[str] = Field(default_factory=list)

    benefits: List[str] = Field(default_factory=list)

    full_description: Optional[str] = Field(
        default=None,
        description="The complete, formatted job description text.",
    )
