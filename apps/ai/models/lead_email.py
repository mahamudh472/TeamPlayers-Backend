"""
Lead outreach email model.

Used by the AI to return a structured email subject and body for cold outreach.
"""

from pydantic import BaseModel, Field


class GeneratedLeadEmail(BaseModel):
    """
    AI-generated outreach email for a recruitment agency lead.
    """

    subject: str = Field(
        description="A compelling, personalized, and concise email subject line tailored to the lead."
    )

    body: str = Field(
        description="A personalized, professional cold outreach email body formatted with clean line breaks. "
        "It should be addressed to the contact person, mention relevant company/hiring details, "
        "introduce recruitment agency capabilities, and end with a courteous, low-friction call to action."
    )
