"""
Company Lead data models.

These models represent structured company profiles extracted from
scraped web datasets, directories, and corporate profiles for B2B lead generation.
"""

from typing import Optional
from pydantic import BaseModel, Field


class CompanyLeadProfile(BaseModel):
    """
    Parsed and verified company lead profile.
    """

    is_company: bool = Field(
        default=True,
        description="True if this is an actual operating company, business, or organization. False if it is a job board, aggregator, blog post, or directory."
    )

    company_name: str = Field(
        default="",
        description="Clean, official company or institution name."
    )

    website: Optional[str] = Field(
        default=None,
        description="Official website URL or company page URL."
    )

    company_domain: Optional[str] = Field(
        default=None,
        description="Primary domain name of the company (e.g. acme.com)."
    )

    linkedin_url: Optional[str] = Field(
        default=None,
        description="Official LinkedIn company profile URL."
    )

    industry: Optional[str] = Field(
        default=None,
        description="Primary industry or sector the company operates in."
    )

    location: Optional[str] = Field(
        default=None,
        description="Headquarters city, region, or country of the company."
    )

    description: Optional[str] = Field(
        default=None,
        description="Brief summary or description of the company's business and activities."
    )

    company_size: Optional[str] = Field(
        default=None,
        description="Estimated employee range (e.g. '1-10', '11-50', '51-200', '201-500', '500+')."
    )

    employee_count: Optional[int] = Field(
        default=None,
        description="Estimated exact employee count if explicitly mentioned."
    )

    parsing_confidence: Optional[float] = Field(
        default=None,
        description="Confidence score from 0.0 to 1.0."
    )
