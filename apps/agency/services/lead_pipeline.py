"""
Hiring-signal lead pipeline.

Stages:
  1. fetch      - recent job postings from LinkedIn (Apify), date-filtered at the source
  2. freshness  - drop anything older than LEAD_MAX_JOB_AGE_DAYS
  3. relevance  - rules (agencies, title overlap) then an LLM check
  4. group      - one lead per company, newest matching job wins
  5. liveness   - confirm the posting page is still open
  6. contacts   - Lusha decision-maker + verified email (top companies only, to save credits)
  7. score      - recency / title match / size fit / contact quality
"""
import re
import logging
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone as dt_timezone
from typing import Optional
from urllib.parse import urlparse

import requests
from django.conf import settings
from django.utils import timezone
from pydantic import BaseModel, Field

from apps.agency.models import Leads
from apps.agency.utils.apify_client import ApifyClient
from apps.agency.utils.lusha_client import LushaClient, LushaError

logger = logging.getLogger(__name__)

AGENCY_NAME_MARKERS = (
    'recruit', 'staffing', 'headhunt', 'executive search', 'talent solutions',
    'personnel', 'manpower', 'randstad', 'adecco', 'hays', 'robert half',
    'workforce', 'employment agency', 'placement',
)
AGENCY_INDUSTRY_MARKERS = ('staffing and recruiting', 'human resources services')
CLOSED_MARKERS = (
    'no longer accepting applications', 'job is no longer available',
    'this job is closed', 'position has been filled', 'no longer available',
)
STOPWORDS = {
    'and', 'or', 'the', 'a', 'an', 'of', 'for', 'in', 'at', 'to', 'with',
    'm', 'w', 'd', 'f', 'mwd', 'senior', 'junior', 'lead', 'sr', 'jr',
}
SMALL_COMPANY_LIMIT = 50


# --------------------------------------------------------------------------- #
# Stage 1: fetch
# --------------------------------------------------------------------------- #
def fetch_recent_jobs(keywords: str, location: str, max_age_days: int) -> list[dict]:
    actor_id = getattr(settings, 'APIFY_LEAD_ACTOR_ID', 'curious_coder/linkedin-jobs-scraper')
    if 'linkedin-jobs-scraper' not in actor_id:
        actor_id = 'curious_coder/linkedin-jobs-scraper'
    date_window = 'past24Hours' if max_age_days <= 1 else ('pastWeek' if max_age_days <= 7 else 'pastMonth')
    run_input = {
        'keywords': keywords,
        'location': location or '',
        'datePosted': date_window,
        'limitPerSource': getattr(settings, 'LEAD_MAX_JOBS_FETCHED', 80),
        'scrapeCompany': True,
    }
    logger.info(f"[LeadPipeline] Fetching jobs: {run_input}")
    return ApifyClient().run_actor(actor_id, run_input, timeout_secs=420, allow_partial=False)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _parse_posted_at(item: dict) -> Optional[datetime]:
    raw = item.get('postedAt')
    if not raw:
        return None
    try:
        dt = datetime.fromisoformat(str(raw).replace('Z', '+00:00'))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=dt_timezone.utc)
    return dt


def _domain_from_url(url: str) -> str:
    if not url:
        return ''
    try:
        netloc = urlparse(url if url.startswith(('http://', 'https://')) else f'https://{url}').netloc.lower()
    except ValueError:
        return ''
    netloc = netloc.removeprefix('www.')
    return '' if 'linkedin.com' in netloc else netloc


SYNONYMS = {'developer': 'engineer', 'programmer': 'engineer', 'swe': 'engineer', 'sde': 'engineer',
            'entwickler': 'engineer', 'ingenieur': 'engineer'}


def _tokens(text: str) -> set:
    raw = re.findall(r'[a-z0-9+#.]+', (text or '').lower())
    return {SYNONYMS.get(t, t) for t in raw if t not in STOPWORDS and len(t) > 1}


def _title_match(target: str, job_title: str) -> float:
    """Share of target-title tokens present in the job title (0..1)."""
    want = _tokens(target)
    if not want:
        return 1.0
    return len(want & _tokens(job_title)) / len(want)


def _company_key(job: dict) -> str:
    return _domain_from_url(job.get('companyWebsite') or '') or re.sub(r'\W+', '', (job.get('companyName') or '').lower())


def _employee_count(job: dict) -> Optional[int]:
    try:
        return int(str(job.get('companyEmployeesCount')).replace(',', ''))
    except (TypeError, ValueError):
        return None


def _size_range(size_str: str) -> Optional[tuple]:
    nums = [int(n.replace(',', '')) for n in re.findall(r'\d[\d,]*', size_str or '')]
    if not nums:
        return None
    return (nums[0], nums[1] if len(nums) > 1 else 10 ** 9)


# --------------------------------------------------------------------------- #
# Stage 2 + 3: freshness and relevance
# --------------------------------------------------------------------------- #
def filter_fresh(jobs: list[dict], max_age_days: int) -> list[dict]:
    cutoff = timezone.now() - timedelta(days=max_age_days)
    fresh = []
    for job in jobs:
        posted = _parse_posted_at(job)
        if not posted or posted < cutoff:
            continue
        job['_posted'] = posted
        fresh.append(job)
    logger.info(f"[LeadPipeline] Freshness: {len(fresh)}/{len(jobs)} within {max_age_days} days")
    return fresh


def filter_by_rules(jobs: list[dict], target_title: str) -> list[dict]:
    kept = []
    for job in jobs:
        name = (job.get('companyName') or '').lower()
        industry = (job.get('industries') or '').lower()
        if not name or any(m in name for m in AGENCY_NAME_MARKERS):
            continue
        if any(m in industry for m in AGENCY_INDUSTRY_MARKERS):
            continue
        job['_title_match'] = _title_match(target_title, job.get('title') or '')
        if target_title and job['_title_match'] < 0.34:
            continue
        kept.append(job)
    logger.info(f"[LeadPipeline] Rules: {len(kept)}/{len(jobs)} kept")
    return kept


class _RelevanceVerdict(BaseModel):
    index: int
    relevant: bool = Field(description="True only if this is a genuine, direct-hire opening matching the target role")


class _RelevanceBatch(BaseModel):
    verdicts: list[_RelevanceVerdict]


def filter_by_llm(jobs: list[dict], target_title: str, industry: str) -> list[dict]:
    """One batched LLM call. Fails open to the rule-filtered list if the model is unavailable."""
    if not jobs or not target_title:
        return jobs
    try:
        from apps.ai.clients.openai_client import get_openai_client
        from apps.ai.config import get_settings
        client, model = get_openai_client(), get_settings().openai_model
        listing = "\n".join(
            f"[{i}] title={j.get('title')!r} | company={j.get('companyName')!r} | "
            f"industry={j.get('industries')!r} | desc={(j.get('descriptionText') or '')[:250]!r}"
            for i, j in enumerate(jobs)
        )
        prompt = (
            f"Target role: {target_title}\nPreferred industry (soft preference): {industry or 'any'}\n\n"
            "For each job, decide if it is a real, direct-hire opening at an operating company for the "
            "target role or a very close equivalent. Reject recruiting/staffing agencies, unrelated roles, "
            "internships/training programs (unless the target is one), and aggregator spam.\n\n" + listing
        )
        response = client.responses.parse(
            model=model,
            input=[
                {"role": "system", "content": "You are a strict B2B recruitment lead qualifier. Return one verdict per job index."},
                {"role": "user", "content": prompt},
            ],
            text_format=_RelevanceBatch,
        )
        ok = {v.index for v in response.output_parsed.verdicts if v.relevant}
        kept = [j for i, j in enumerate(jobs) if i in ok]
        logger.info(f"[LeadPipeline] LLM relevance: {len(kept)}/{len(jobs)} kept")
        return kept
    except Exception as e:
        logger.warning(f"[LeadPipeline] LLM relevance check skipped: {e}")
        return jobs


# --------------------------------------------------------------------------- #
# Stage 4: group by company
# --------------------------------------------------------------------------- #
def group_by_company(jobs: list[dict]) -> list[dict]:
    groups: dict[str, dict] = {}
    for job in sorted(jobs, key=lambda j: j['_posted'], reverse=True):
        key = _company_key(job)
        if not key:
            continue
        if key in groups:
            groups[key]['open_roles'] += 1
        else:
            groups[key] = {'job': job, 'open_roles': 1, 'key': key}
    return list(groups.values())


# --------------------------------------------------------------------------- #
# Stage 5: liveness
# --------------------------------------------------------------------------- #
def _is_live(job: dict) -> bool:
    url = (job.get('link') or '').split('?')[0]
    if not url:
        return True
    try:
        res = requests.get(url, timeout=12, headers={'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64)'})
    except requests.RequestException:
        return True  # unknown -> don't punish
    if res.status_code in (404, 410):
        return False
    body = res.text.lower() if res.ok else ''
    return not any(m in body for m in CLOSED_MARKERS)


def filter_live(companies: list[dict]) -> list[dict]:
    with ThreadPoolExecutor(max_workers=8) as pool:
        flags = list(pool.map(lambda c: _is_live(c['job']), companies))
    live = [c for c, ok in zip(companies, flags) if ok]
    logger.info(f"[LeadPipeline] Liveness: {len(live)}/{len(companies)} still open")
    return live


# --------------------------------------------------------------------------- #
# Stage 6: contacts via Lusha
# --------------------------------------------------------------------------- #
HR_TITLES = ['Head of Talent', 'Talent Acquisition', 'Recruiter', 'Recruiting Manager',
             'HR Manager', 'Head of HR', 'Human Resources', 'People Operations', 'Hiring Manager']
FOUNDER_TITLES = ['Founder', 'Co-Founder', 'CEO', 'Managing Director', 'Owner', 'General Manager']


def _contact_rank(title: str, small_company: bool) -> int:
    t = (title or '').lower()
    founder = any(k in t for k in ('founder', 'ceo', 'owner', 'managing director', 'general manager'))
    hr = any(k in t for k in ('talent', 'recruit', 'hr', 'human resources', 'people'))
    if small_company:
        return 0 if founder else (1 if hr else 2)
    return 0 if hr else (1 if founder else 2)


def find_contact(lusha: LushaClient, domain: str, employees: Optional[int]) -> Optional[dict]:
    small = employees is not None and employees <= SMALL_COMPANY_LIMIT
    titles = (FOUNDER_TITLES + HR_TITLES) if small else (HR_TITLES + FOUNDER_TITLES)
    previews = lusha.search_contacts(domain, titles)
    if not previews:
        return None
    previews.sort(key=lambda p: _contact_rank((p.get('jobTitle') or {}).get('title'), small))
    enriched = lusha.enrich_contacts([previews[0]['id']], reveal=('emails', 'phones'))
    if not enriched:
        return None
    c = enriched[0]
    emails = sorted(
        [e for e in (c.get('emails') or []) if e.get('email')],
        key=lambda e: (e.get('type') != 'work', e.get('confidence') or 'Z'),
    )
    phones = c.get('phones') or []
    return {
        'name': c.get('fullName') or f"{c.get('firstName', '')} {c.get('lastName', '')}".strip(),
        'title': (c.get('jobTitle') or {}).get('title'),
        'email': emails[0]['email'] if emails else None,
        'email_confidence': emails[0].get('confidence') if emails else None,
        'phone': phones[0].get('number') if phones else None,
    }


# --------------------------------------------------------------------------- #
# Stage 7: score
# --------------------------------------------------------------------------- #
def _base_score(company: dict, size_pref: str) -> int:
    job = company['job']
    age_days = max((timezone.now() - job['_posted']).total_seconds() / 86400, 0)
    score = max(0, 40 - int(age_days * 3))                      # recency 0..40
    score += int(job.get('_title_match', 1.0) * 30)             # title fit 0..30
    score += min(company['open_roles'] - 1, 2) * 5              # multiple openings 0..10
    rng, emp = _size_range(size_pref), _employee_count(job)
    if rng and emp is not None and rng[0] <= emp <= rng[1]:
        score += 10                                             # size fit
    return score


def _priority(score: int) -> str:
    return 'high' if score >= 70 else ('medium' if score >= 45 else 'low')


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
def build_leads(country: str, industry: str, job_title: str, company_size: str, hiring_activity: str,
                existing_keys: set) -> list[dict]:
    max_age = getattr(settings, 'LEAD_MAX_JOB_AGE_DAYS', 14)
    keywords = job_title or industry or ''
    if not keywords:
        return []

    jobs = fetch_recent_jobs(keywords, country, max_age)
    logger.info(f"[LeadPipeline] Fetched {len(jobs)} raw jobs")
    jobs = filter_by_llm(filter_by_rules(filter_fresh(jobs, max_age), job_title), job_title, industry)

    companies = [c for c in group_by_company(jobs) if c['key'] not in existing_keys]
    for c in companies:
        c['score'] = _base_score(c, company_size)
    companies.sort(key=lambda c: c['score'], reverse=True)
    companies = filter_live(companies[: getattr(settings, 'LEAD_MAX_ENRICHED_COMPANIES', 25) * 2])

    lusha = LushaClient()
    require_email = getattr(settings, 'LEAD_REQUIRE_CONTACT_EMAIL', False) and lusha.configured
    budget = getattr(settings, 'LEAD_MAX_ENRICHED_COMPANIES', 25)
    leads = []
    for c in companies:
        job = c['job']
        domain = _domain_from_url(job.get('companyWebsite') or '')
        contact = None
        if lusha.configured and domain and budget > 0:
            budget -= 1
            try:
                contact = find_contact(lusha, domain, _employee_count(job))
            except LushaError as e:
                logger.warning(f"[LeadPipeline] Lusha failed for {domain}: {e}")
        if require_email and not (contact and contact.get('email')):
            continue

        score = c['score'] + (10 if contact and contact.get('email') else 0)
        title_l = (job.get('title') or '').lower()
        emp = _employee_count(job)
        leads.append({
            'company': (job.get('companyName') or '')[:100],
            'website': (job.get('companyWebsite') or '')[:255] or None,
            'company_domain': domain or None,
            'linkedin': (job.get('companyLinkedinUrl') or '').split('?')[0][:255] or None,
            'industry': (job.get('industries') or industry or '')[:100] or None,
            'company_size': (company_size or '')[:100] or None,
            'employee_count': emp,
            'location': (job.get('location') or country or '')[:100] or None,
            'hiring_activity': hiring_activity or 'Active',
            'job_title': (job.get('title') or '')[:255],
            'job_type': (job.get('employmentType') or '')[:100] or None,
            'job_level': (job.get('seniorityLevel') or '')[:100] or None,
            'is_remote': 'remote' in title_l or 'remote' in (job.get('location') or '').lower(),
            'job_url': (job.get('link') or '').split('?')[0][:500] or None,
            'job_posted_at': job['_posted'],
            'open_roles_count': c['open_roles'],
            'description': (job.get('companyDescription') or '')[:2000] or None,
            'contact_person': (contact or {}).get('name') or None,
            'contact_title': (contact or {}).get('title') or None,
            'contact_email': (contact or {}).get('email'),
            'contact_phone': (contact or {}).get('phone'),
            'email_confidence': (contact or {}).get('email_confidence'),
            'lead_score': min(score, 100),
            'priority': _priority(score),
            'source': 'linkedin_jobs',
            'status': 'new',
            'detected_at': timezone.now(),
            'domain_source': 'apify',
            'enriched_at': timezone.now() if contact else None,
        })
    leads.sort(key=lambda l: l['lead_score'], reverse=True)
    logger.info(f"[LeadPipeline] Built {len(leads)} leads "
                f"({sum(1 for l in leads if l['contact_email'])} with email)")
    return leads


def existing_company_keys(agency) -> set:
    """Companies the agency already has, so repeated runs surface only new opportunities."""
    keys = set()
    for domain, name in Leads.objects.filter(agency=agency).values_list('company_domain', 'company'):
        if domain:
            keys.add(domain.lower())
        keys.add(re.sub(r'\W+', '', (name or '').lower()))
    return keys
