"""
Candidate data models.

These models represent a parsed candidate profile after importing
a CV, RecruitCRM export, Bullhorn export, LinkedIn profile,
manual entry, or other supported sources.
"""

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class Experience(BaseModel):
    """
    Candidate work experience.
    """

    company: str = ""
    job_title: str = ""
    employment_type: Optional[str] = None

    start_date: Optional[str] = None
    end_date: Optional[str] = None

    duration: Optional[str] = None

    location: Optional[str] = None

    description: Optional[str] = None


class Education(BaseModel):
    """
    Candidate education.
    """

    institution: str = ""
    degree: str = ""
    field_of_study: Optional[str] = None

    start_year: Optional[str] = None
    end_year: Optional[str] = None

    grade: Optional[str] = None


class Certification(BaseModel):
    """
    Professional certification.
    """

    name: str = ""

    organization: Optional[str] = None

    issue_date: Optional[str] = None

    expiry_date: Optional[str] = None


class CandidateProfile(BaseModel):
    """
    Parsed candidate profile.
    """

    # Basic Information

    full_name: str = ""

    email: Optional[EmailStr] = None

    phone: Optional[str] = None

    location: Optional[str] = None

    linkedin_url: Optional[str] = None

    portfolio_url: Optional[str] = None

    # Current Position

    current_job_title: Optional[str] = None

    current_company: Optional[str] = None

    total_experience_years: Optional[float] = None

    # Candidate Details

    expected_salary: Optional[str] = None

    current_salary: Optional[str] = None

    notice_period: Optional[str] = None

    willing_to_relocate: Optional[bool] = None

    # Skills

    technical_skills: List[str] = Field(default_factory=list)

    soft_skills: List[str] = Field(default_factory=list)

    languages: List[str] = Field(default_factory=list)

    certifications: List[Certification] = Field(default_factory=list)

    # Career

    experiences: List[Experience] = Field(default_factory=list)

    education: List[Education] = Field(default_factory=list)

    industry_experience: List[str] = Field(default_factory=list)

    # AI Metadata

    source: Optional[str] = None

    raw_text: Optional[str] = None

    parsing_confidence: Optional[float] = None
