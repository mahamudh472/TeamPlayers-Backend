import logging
import threading
from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.agency.models import Agency, LeadGenerationSession, Activity
from apps.accounts.models import User
from apps.agency.services.leads import ingest_bulk_leads
from apps.agency.services.lead_pipeline import build_leads, existing_company_keys

logger = logging.getLogger(__name__)

def create_lead_generation_session(
    agency: Agency,
    user: User,
    country: str,
    industry: str,
    company_size: str = None,
    hiring_activity: str = None,
    job_title: str = None
) -> LeadGenerationSession:
    """
    Creates and saves a LeadGenerationSession object.
    """
    return LeadGenerationSession.objects.create(
        agency=agency,
        user=user,
        country=country,
        industry=industry,
        job_title=job_title or None,
        company_size=company_size,
        hiring_activity=hiring_activity,
        status='pending'
    )


def trigger_lead_generation(session: LeadGenerationSession) -> None:
    """
    Unified entry point to trigger lead generation based on the configured provider.
    Toggled via settings.LEAD_GENERATION_PROVIDER ('n8n' or 'apify').
    """
    provider = getattr(settings, 'LEAD_GENERATION_PROVIDER', 'n8n').lower()

    if provider == 'apify':
        trigger_apify_lead_generation(session)
    else:
        trigger_n8n_lead_generation(session)


def trigger_n8n_lead_generation(session: LeadGenerationSession) -> None:
    """
    Triggers the n8n lead generation workflow via webhook.
    """
    import requests
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
        'job_title': session.job_title,
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


def trigger_apify_lead_generation(session: LeadGenerationSession) -> None:
    """
    Triggers backend lead generation via Apify in a background thread.
    """
    api_key = getattr(settings, 'APIFY_API_KEY', '')
    if not api_key:
        session.status = 'failed'
        session.save(update_fields=['status'])
        logger.error("APIFY_API_KEY is not configured in settings.")
        raise ValidationError({"detail": "Lead generation service is not configured (missing APIFY_API_KEY)."})

    session.status = 'processing'
    session.save(update_fields=['status'])

    thread = threading.Thread(
        target=_process_apify_lead_generation_in_background,
        args=(str(session.id), session.agency.id, str(session.user.id) if session.user else None)
    )
    thread.daemon = True
    thread.start()


def _process_apify_lead_generation_in_background(session_id: str, agency_id: int, user_id: str = None) -> None:
    """
    Background worker: runs the hiring-signal pipeline (recent jobs -> relevance -> contacts)
    and stores the resulting leads.
    """
    try:
        session = LeadGenerationSession.objects.get(id=session_id)
        agency = Agency.objects.get(id=agency_id)
        user = User.objects.get(id=user_id) if user_id else None

        logger.info(
            f"[LeadGeneration] Session={session_id} | job_title='{session.job_title}', "
            f"industry='{session.industry}', country='{session.country}'"
        )

        leads_data = build_leads(
            country=session.country or '',
            industry=session.industry or '',
            job_title=session.job_title or '',
            company_size=session.company_size or '',
            hiring_activity=session.hiring_activity or '',
            existing_keys=existing_company_keys(agency),
        )

        created_leads = ingest_bulk_leads(agency, leads_data, user=user) if leads_data else []

        session.status = 'completed'
        session.save(update_fields=['status'])

        if user:
            from apps.notifications.services.notifications import create_notification
            try:
                target_desc = f"{session.industry or 'industry'} in {session.country or 'target region'}"
                if session.job_title:
                    target_desc += f" hiring for {session.job_title}"

                if created_leads:
                    with_email = sum(1 for l in created_leads if l.contact_email)
                    msg = (f"Lead generation completed. {len(created_leads)} recently-hiring companies found "
                           f"for {target_desc} ({with_email} with a contact email).")
                else:
                    msg = f"Lead generation completed for {target_desc}. No new recently-hiring companies matched."

                create_notification(
                    user=user,
                    title="Lead Generation Complete",
                    message=msg,
                    notification_type="lead_generation_complete",
                    source={"session_id": str(session.id)}
                )
            except Exception as notif_err:
                logger.error(f"Failed to send lead generation notification: {notif_err}")

    except Exception as e:
        logger.exception(f"Error in lead generation background task for session {session_id}: {e}")
        try:
            LeadGenerationSession.objects.filter(id=session_id).update(status='failed')
        except Exception:
            pass
    finally:
        close_old_connections()
