"""
Lead outreach email generator using OpenAI.
"""

import logging
from typing import Optional, Dict, Any
from openai import OpenAI

from apps.ai.clients.openai_client import get_openai_client
from apps.ai.config import get_settings
from apps.ai.models.lead_email import GeneratedLeadEmail
from apps.ai.prompts_loader import load_prompt

logger = logging.getLogger(__name__)


class LeadEmailGenerator:
    """
    Generate tailored outreach email for a prospective client lead.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.system_prompt = load_prompt("lead_email_generator_prompt.txt")

    def _get_fallback_email(
        self,
        lead_data: Dict[str, Any],
        sender_name: str,
        agency_name: str
    ) -> GeneratedLeadEmail:
        company = lead_data.get("company") or "your team"
        contact_person = lead_data.get("contact_person")
        greeting = f"Hi {contact_person.split()[0]}," if contact_person else f"Hi {company} Hiring Team,"
        industry = lead_data.get("industry") or "your sector"
        job_title = lead_data.get("job_title")

        if job_title:
            subject = f"Relevant {job_title} profiles for {company}"
            opening_sentence = (
                f"I noticed you were recruiting for a {job_title} at {company}. "
                f"As specialist recruiters for the {industry} sector, we currently have a number of "
                f"relevant, pre-vetted profiles for your {job_title} role from many of your competitors in the market."
            )
        else:
            subject = f"Specialist {industry} talent pipeline for {company}"
            opening_sentence = (
                f"I noticed {company}'s ongoing talent recruitment in the {industry} space. "
                f"As specialist recruiters in {industry}, we currently have a number of relevant, pre-vetted profiles "
                f"from key competitors in the market."
            )

        body_lines = [
            greeting,
            "",
            opening_sentence,
            "",
            "I thought I would reach out to see if it makes sense to send some matching profiles through to you and start a discussion about how we can support you to fill this role.",
            "",
            "Our services are free of charge until the start date of an actual placement, so this is a risk-free opportunity for you to review the best talent in the market for your vacancy.",
            "",
            "Would you be open to reviewing a couple of matching candidate profiles or having a brief 10-minute introductory call later this week?",
            "",
            f"Best regards,\n{sender_name or 'Recruitment Team'}\n{agency_name or 'TeamPlayers'}"
        ]

        return GeneratedLeadEmail(
            subject=subject,
            body="\n".join(body_lines)
        )

    def generate(
        self,
        lead_data: Dict[str, Any],
        sender_name: str = "",
        agency_name: str = ""
    ) -> GeneratedLeadEmail:
        """
        Generate outreach email subject and body for a lead.
        """
        prompt_input = (
            f"Agency Name: {agency_name or 'TeamPlayers'}\n"
            f"Sender Name: {sender_name or 'Recruiter'}\n"
            f"Target Company: {lead_data.get('company', 'Unknown')}\n"
            f"Contact Person: {lead_data.get('contact_person', 'Hiring Manager')}\n"
            f"Industry: {lead_data.get('industry', 'N/A')}\n"
            f"Location: {lead_data.get('location', 'N/A')}\n"
            f"Company Size: {lead_data.get('company_size', 'N/A')}\n"
            f"Hiring Activity: {lead_data.get('hiring_activity', 'N/A')}\n"
            f"Target Job Opening (X): {lead_data.get('job_title', 'N/A')}\n"
            f"Job Description / Details: {lead_data.get('description', 'N/A')}\n"
            f"Website: {lead_data.get('website', 'N/A')}\n"
        )

        try:
            client: OpenAI = get_openai_client()
            # Try structured response via responses API
            try:
                response = client.responses.parse(
                    model=self.settings.openai_model,
                    input=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt_input},
                    ],
                    text_format=GeneratedLeadEmail,
                )
                if response.output_parsed:
                    return response.output_parsed
            except Exception as e_resp:
                logger.info(f"[LeadEmailGenerator] responses.parse fallback to beta.chat.completions: {e_resp}")
                response = client.beta.chat.completions.parse(
                    model=self.settings.openai_model,
                    messages=[
                        {"role": "system", "content": self.system_prompt},
                        {"role": "user", "content": prompt_input},
                    ],
                    response_format=GeneratedLeadEmail,
                )
                if response.choices and response.choices[0].message.parsed:
                    return response.choices[0].message.parsed
        except Exception as e:
            logger.error(f"[LeadEmailGenerator] Failed to generate AI email: {e}")

        return self._get_fallback_email(lead_data, sender_name, agency_name)
