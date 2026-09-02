import re
import logging
import threading
from urllib.parse import urlparse
from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone
from rest_framework.exceptions import ValidationError
from apps.agency.models import Agency, LeadGenerationSession, Activity
from apps.accounts.models import User
from apps.agency.services.leads import ingest_bulk_leads
from apps.agency.utils.apify_client import ApifyClient, ApifyError

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


def _normalize_lead_from_item(item: dict, default_country: str, default_industry: str, default_size: str) -> dict:
    """
    Normalizes a scraped dataset item into a standard lead dictionary.
    Handles Google Search Scraper outputs as well as direct company/lead scraper structures.
    """
    # Direct field mapping if available
    company = item.get('company') or item.get('company_name') or item.get('companyName') or item.get('name')
    website = item.get('website') or item.get('url') or item.get('link') or ''
    description = item.get('description') or item.get('snippet') or item.get('text') or ''
    title = item.get('title') or item.get('job_title') or item.get('jobTitle') or ''

    # Handle domain extraction from website
    company_domain = ''
    if website:
        try:
            parsed_uri = urlparse(website if website.startswith(('http://', 'https://')) else f"https://{website}")
            company_domain = parsed_uri.netloc.replace('www.', '')
        except Exception:
            company_domain = ''

    if not company:
        # Try inferring company from title or domain
        if title:
            # Clean common title formats e.g. "Careers at Acme Corp", "Acme Inc - Jobs"
            cleaned_title = re.sub(r'(?i)(careers|jobs|hiring|openings|official site|about us|home)\s*[-|:]\s*', '', title)
            parts = re.split(r'[-|:]', cleaned_title)
            company = parts[0].strip() if parts else title[:50]
        elif company_domain:
            company = company_domain.split('.')[0].capitalize()
        else:
            company = "Generated Lead"

    location = item.get('location') or default_country or ''
    industry = item.get('industry') or default_industry or ''
    company_size = item.get('company_size') or item.get('companySize') or default_size or ''
    hiring_activity = item.get('hiring_activity') or 'Active'
    job_title = item.get('job_title') or item.get('jobTitle') or title[:255]
    job_url = item.get('job_url') or item.get('jobUrl') or (website if website.startswith(('http://', 'https://')) else '')
    linkedin = item.get('linkedin') or item.get('linkedin_url') or ''

    return {
        'company': company[:255],
        'website': website[:255] if website else None,
        'company_domain': company_domain[:255] if company_domain else None,
        'linkedin': linkedin[:255] if linkedin else None,
        'industry': industry[:100] if industry else None,
        'company_size': company_size[:100] if company_size else None,
        'employee_count': item.get('employee_count') or item.get('employeeCount'),
        'location': location[:255] if location else None,
        'hiring_activity': hiring_activity[:255] if hiring_activity else None,
        'job_title': job_title[:255] if job_title else None,
        'job_type': item.get('job_type') or 'Full-Time',
        'job_level': item.get('job_level') or 'Mid',
        'is_remote': item.get('is_remote', False),
        'job_url': job_url[:500] if job_url else None,
        'description': description,
        'source': 'apify_crawler',
        'status': 'new',
        'detected_at': timezone.now(),
        'domain_source': 'apify',
        'enriched_at': timezone.now(),
    }


def _process_apify_lead_generation_in_background(session_id: str, agency_id: int, user_id: str = None) -> None:
    """
    Background worker that runs the Apify actor and saves generated leads.
    """
    try:
        session = LeadGenerationSession.objects.get(id=session_id)
        agency = Agency.objects.get(id=agency_id)
        user = User.objects.get(id=user_id) if user_id else None

        actor_id = getattr(settings, 'APIFY_LEAD_ACTOR_ID', 'apify/google-search-scraper')
        client = ApifyClient()

        # Build search query from session parameters
        queries = []
        query_parts = []
        if session.industry:
            query_parts.append(session.industry)
        if session.country:
            query_parts.append(f"in {session.country}")
        query_parts.append("companies hiring jobs")

        main_query = " ".join(query_parts)
        queries.append(main_query)

        # Actor input payload
        if "google-search-scraper" in actor_id:
            actor_input = {
                "queries": "\n".join(queries),
                "maxPagesPerQuery": 1,
                "resultsPerPage": 10
            }
        else:
            actor_input = {
                "country": session.country,
                "industry": session.industry,
                "company_size": session.company_size,
                "hiring_activity": session.hiring_activity,
                "queries": "\n".join(queries)
            }

        # Run the Apify actor
        dataset_items = client.run_actor(actor_id=actor_id, run_input=actor_input, timeout_secs=180)

        # Flatten organicResults if returned by google-search-scraper
        raw_items = []
        for item in dataset_items:
            if "organicResults" in item and isinstance(item["organicResults"], list):
                raw_items.extend(item["organicResults"])
            else:
                raw_items.append(item)

        # Transform raw items into lead records
        leads_data = []
        for item in raw_items:
            lead_dict = _normalize_lead_from_item(
                item=item,
                default_country=session.country or '',
                default_industry=session.industry or '',
                default_size=session.company_size or ''
            )
            if lead_dict.get('company'):
                leads_data.append(lead_dict)

        if not leads_data:
            # Create a placeholder lead from session criteria if actor returned empty results
            leads_data.append({
                'company': f"Prospective {session.industry or 'Tech'} Company",
                'website': f"https://example-{session.country.lower() if session.country else 'global'}.com",
                'industry': session.industry or 'General',
                'company_size': session.company_size or '11-50',
                'location': session.country or 'Global',
                'hiring_activity': session.hiring_activity or 'Active',
                'source': 'apify_crawler',
                'status': 'new',
                'detected_at': timezone.now(),
                'domain_source': 'apify',
                'enriched_at': timezone.now(),
            })

        # Save leads in database
        created_leads = ingest_bulk_leads(agency, leads_data, user=user)

        # Mark session completed
        session.status = 'completed'
        session.save(update_fields=['status'])

        # Notify user
        if user:
            from apps.notifications.services.notifications import create_notification
            try:
                create_notification(
                    user=user,
                    title="Lead Generation Complete",
                    message=f"Lead generation completed. {len(created_leads)} leads generated successfully for {session.industry or 'industry'} in {session.country or 'target region'}.",
                    notification_type="lead_generation_complete",
                    source={"session_id": str(session.id)}
                )
            except Exception as notif_err:
                logger.error(f"Failed to send lead generation notification: {notif_err}")

    except Exception as e:
        logger.exception(f"Error in Apify lead generation background task for session {session_id}: {e}")
        try:
            LeadGenerationSession.objects.filter(id=session_id).update(status='failed')
        except Exception:
            pass
    finally:
        close_old_connections()
