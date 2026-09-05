import re
import json
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
from apps.ai.company_parser import CompanyParser

logger = logging.getLogger(__name__)

JUNK_URL_PATTERNS = [
    '/jobs/', '/job/', '/careers/', '/vacancies/', '/openings/',
    'indeed.com', 'glassdoor.com', 'monster.com', 'ziprecruiter.com',
    'jooble.org', 'reliefweb.int', 'salary.com', 'upwork.com',
    'fiverr.com', 'jobs.af', 'bayt.com', 'naukri.com', 'simplyhired.com'
]

JUNK_TITLE_PATTERNS = [
    'vacancies in', 'vacancies', 'jobs in', 'open roles', 'job openings', 'open positions',
    'positions in', 'hiring now', 'careers in', 'careers at', 'top 10', 'how to',
    'guide to', 'guide for', 'directory of', 'list of companies', 'salary for',
    'salaries in', 'employment in', 'work in', 'all jobs', 'latest jobs',
    'job board', 'find a job', 'apply now', '10 best', 'recruitment in',
    'job opportunities', 'hiring jobs', 'open jobs', 'open role'
]


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


def _clean_company_name_heuristic(title: str, raw_url: str = '') -> str:
    """
    Extracts a clean, human-readable company name from search result title and URL.
    """
    slug_name = ''
    if raw_url and 'linkedin.com/company/' in raw_url:
        match = re.search(r'linkedin\.com/company/([^/?#]+)', raw_url)
        if match:
            slug = match.group(1).replace('-', ' ').replace('_', ' ')
            slug_name = ' '.join([w.capitalize() for w in slug.split()])

    cleaned = re.sub(r'(?i)\s*[-|:|–|—|•|\|]\s*(LinkedIn|Overview|About Us|About|Home|Careers|Official Site|Official Website|Company Page).*$', '', title)
    cleaned = re.sub(r'(?i)^(Welcome to|Home of)\s+', '', cleaned)
    cleaned = re.sub(r'\.\.\.$', '', cleaned).strip()

    # If title was truncated or left with trailing preposition, prefer clean slug name
    if (cleaned.endswith((' for', ' in', ' and', ' of', ' the', ' with', ' at')) or len(cleaned) < 3) and slug_name:
        return slug_name

    return cleaned or slug_name


def _normalize_lead_from_item(
    item: dict,
    default_country: str,
    default_industry: str,
    default_size: str,
    company_parser: CompanyParser = None
) -> dict:
    """
    Normalizes a scraped dataset item into a standard genuine company lead dictionary.
    Strictly filters out non-company posts, job boards, aggregators, and generic articles.
    """
    raw_url = item.get('url') or item.get('link') or item.get('website') or ''
    title = item.get('title') or item.get('job_title') or item.get('jobTitle') or ''
    snippet = item.get('description') or item.get('snippet') or item.get('text') or ''

    # 1. URL Blacklist Filter
    if raw_url:
        raw_url_lower = raw_url.lower()
        if any(bad_pattern in raw_url_lower for bad_pattern in JUNK_URL_PATTERNS):
            logger.debug(f"[LeadGeneration] Skipping junk URL: {raw_url}")
            return None

    # 2. Title Blacklist Filter
    title_lower = title.lower()
    if any(junk_title in title_lower for junk_title in JUNK_TITLE_PATTERNS):
        logger.debug(f"[LeadGeneration] Skipping junk title: {title}")
        return None

    # 3. Use AI Company Parser to extract & verify genuine company entity
    parsed_profile = None
    if company_parser:
        prompt_context = (
            f"Title: {title}\n"
            f"URL: {raw_url}\n"
            f"Snippet: {snippet}\n"
            f"Default Industry: {default_industry}\n"
            f"Default Country: {default_country}\n"
        )
        parsed_profile = company_parser.parse_company(prompt_context)

    if parsed_profile:
        if not parsed_profile.is_company:
            logger.info(f"[LeadGeneration] AI determined entity is not a company: '{title}' (URL: {raw_url}), skipping.")
            return None

        company_name = parsed_profile.company_name
        website = parsed_profile.website or raw_url
        linkedin_url = parsed_profile.linkedin_url or (raw_url if 'linkedin.com/company/' in raw_url else '')
        industry = parsed_profile.industry or default_industry
        location = parsed_profile.location or default_country
        description = parsed_profile.description or snippet
        company_size = parsed_profile.company_size or default_size
        employee_count = parsed_profile.employee_count
        company_domain = parsed_profile.company_domain
    else:
        # Heuristic fallback if AI parser is unavailable
        company_name = _clean_company_name_heuristic(title, raw_url)
        website = raw_url
        linkedin_url = raw_url if 'linkedin.com/company/' in raw_url else ''
        industry = default_industry
        location = default_country
        description = re.sub(r'\s*\.\.\.Read more$', '', snippet).strip()
        company_size = default_size
        employee_count = item.get('employee_count') or item.get('employeeCount')
        company_domain = ''

    # 4. Strict Heuristic Verification
    if not company_name:
        return None

    # Discard if company name is just generic single industry/country word
    name_clean = company_name.strip().lower()
    generic_words = [
        'finance', 'automotive', 'software', 'technology', 'jobs', 'vacancies',
        'employment', 'careers', 'afghanistan', 'germany', 'united states',
        'recruitment', 'candidates'
    ]
    if name_clean in generic_words or len(name_clean) < 2:
        logger.debug(f"[LeadGeneration] Skipping generic company name: '{company_name}'")
        return None

    if any(junk in name_clean for junk in JUNK_TITLE_PATTERNS):
        logger.debug(f"[LeadGeneration] Skipping junk-named company: '{company_name}'")
        return None

    # Derive company_domain if missing
    if not company_domain and website:
        try:
            parsed_uri = urlparse(website if website.startswith(('http://', 'https://')) else f"https://{website}")
            netloc = parsed_uri.netloc.replace('www.', '')
            if 'linkedin.com' not in netloc:
                company_domain = netloc
        except Exception:
            company_domain = ''

    return {
        'company': company_name[:100],
        'website': website[:255] if website else None,
        'company_domain': company_domain[:255] if company_domain else None,
        'linkedin': linkedin_url[:255] if linkedin_url else None,
        'industry': industry[:100] if industry else None,
        'company_size': company_size[:100] if company_size else None,
        'employee_count': employee_count,
        'location': location[:100] if location else None,
        'hiring_activity': 'Active',
        'job_title': None,
        'job_type': 'Full-Time',
        'job_level': 'Mid',
        'is_remote': False,
        'job_url': None,
        'description': description,
        'source': 'apify_crawler',
        'status': 'new',
        'detected_at': timezone.now(),
        'domain_source': 'apify',
        'enriched_at': timezone.now(),
    }


def _process_apify_lead_generation_in_background(session_id: str, agency_id: int, user_id: str = None) -> None:
    """
    Background worker that runs the Apify actor, normalizes and verifies authentic companies,
    and stores generated leads in the database.
    """
    try:
        session = LeadGenerationSession.objects.get(id=session_id)
        agency = Agency.objects.get(id=agency_id)
        user = User.objects.get(id=user_id) if user_id else None

        actor_id = getattr(settings, 'APIFY_LEAD_ACTOR_ID', 'apify/google-search-scraper')
        client = ApifyClient()

        # Build targeted search query for genuine companies on LinkedIn
        industry_term = session.industry.strip() if session.industry else ""
        country_term = session.country.strip() if session.country else ""

        query_parts = []
        if industry_term:
            query_parts.append(f'"{industry_term}"')
        if country_term:
            query_parts.append(f'"{country_term}"')

        combined_terms = " ".join(query_parts) if query_parts else "Companies"
        linkedin_query = f'site:linkedin.com/company/ {combined_terms}'.strip()

        logger.info(
            f"[LeadGeneration] Session={session_id} | Starting Apify run. "
            f"Target Query='{linkedin_query}', Industry='{session.industry}', Country='{session.country}'"
        )

        # Actor input payload
        if "google-search-scraper" in actor_id:
            actor_input = {
                "queries": linkedin_query,
                "maxPagesPerQuery": 1,
                "resultsPerPage": 15
            }
        else:
            actor_input = {
                "country": session.country,
                "industry": session.industry,
                "company_size": session.company_size,
                "hiring_activity": session.hiring_activity,
                "queries": linkedin_query
            }

        logger.info(f"[LeadGeneration] Apify Actor ID: '{actor_id}' | Payload sent: {json.dumps(actor_input, default=str)}")

        # Run the Apify actor
        dataset_items = client.run_actor(actor_id=actor_id, run_input=actor_input, timeout_secs=180)

        # Flatten organicResults if returned by google-search-scraper
        raw_items = []
        for item in dataset_items:
            if "organicResults" in item and isinstance(item["organicResults"], list):
                raw_items.extend(item["organicResults"])
            else:
                raw_items.append(item)

        logger.info(f"[LeadGeneration] Received {len(dataset_items)} dataset items ({len(raw_items)} raw items) from Apify.")

        # Initialize CompanyParser
        company_parser = None
        try:
            company_parser = CompanyParser()
        except Exception as parser_err:
            logger.warning(f"[LeadGeneration] Could not initialize CompanyParser: {parser_err}")

        # Transform and validate raw items into genuine company leads
        leads_data = []
        seen_companies = set()

        for item in raw_items:
            lead_dict = _normalize_lead_from_item(
                item=item,
                default_country=session.country or '',
                default_industry=session.industry or '',
                default_size=session.company_size or '',
                company_parser=company_parser
            )
            if lead_dict and lead_dict.get('company'):
                comp_key = lead_dict['company'].lower()
                if comp_key not in seen_companies:
                    seen_companies.add(comp_key)
                    leads_data.append(lead_dict)

        logger.info(f"[LeadGeneration] Extracted {len(leads_data)} verified company leads out of {len(raw_items)} items.")

        created_leads = []
        if leads_data:
            created_leads = ingest_bulk_leads(agency, leads_data, user=user)

        # Mark session completed
        session.status = 'completed'
        session.save(update_fields=['status'])

        # Notify user
        if user:
            from apps.notifications.services.notifications import create_notification
            try:
                if created_leads:
                    msg = f"Lead generation completed. {len(created_leads)} verified company leads found for {session.industry or 'industry'} in {session.country or 'target region'}."
                else:
                    msg = f"Lead generation completed for {session.industry or 'industry'} in {session.country or 'target region'}. No new company profiles were found matching criteria."

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
        logger.exception(f"Error in Apify lead generation background task for session {session_id}: {e}")
        try:
            LeadGenerationSession.objects.filter(id=session_id).update(status='failed')
        except Exception:
            pass
    finally:
        close_old_connections()
