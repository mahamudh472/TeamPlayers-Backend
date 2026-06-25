from httpcore import request
import requests
import logging
from django.conf import settings
from apps.agency.models import Agency, LeadGenerationSession
from apps.accounts.models import User
from rest_framework.exceptions import ValidationError

logger = logging.getLogger(__name__)

def create_lead_generation_session(
    agency: Agency,
    user: User,
    country: str,
    industry: str,
    company_size: str,
    hiring_activity: str
) -> LeadGenerationSession:
    """
    Creates and saves a LeadGenerationSession object.
    """
    return LeadGenerationSession.objects.create(
        agency=agency,
        user=user,
        country=country,
        industry=industry,
        company_size=company_size,
        hiring_activity=hiring_activity,
        status='pending'
    )

def trigger_n8n_lead_generation(session: LeadGenerationSession) -> None:
    """
    Triggers the n8n lead generation workflow via webhook.
    """
    webhook_url = getattr(settings, 'N8N_WEBHOOK_URL', None)
    if not webhook_url:
        session.status = 'failed'
        session.save(update_fields=['status'])
        logger.error("N8N_WEBHOOK_URL is not configured in settings.")
        raise ValidationError({"detail": "Lead generation service is not configured (missing N8N_WEBHOOK_URL)."})

    payload = {
        'session_id': str(session.id),
        'agency_id': session.agency.id,
        'user_id': str(session.user.id),
        'country': session.country,
        'industry': session.industry,
        'company_size': session.company_size,
        'hiring_activity': session.hiring_activity
    }

    try:
        session.status = 'processing'
        session.save(update_fields=['status'])

        response = requests.post(
            webhook_url,
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )

        response.raise_for_status()
    except requests.RequestException as e:
        session.status = 'failed'
        session.save(update_fields=['status'])
        logger.exception("Failed to send webhook request to n8n.")
        raise ValidationError({"detail": f"Failed to initiate lead generation with n8n workflow: {str(e)}"})
