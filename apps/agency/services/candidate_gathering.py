import re
import json
import logging
import requests
import threading
from urllib.parse import quote_plus
from django.conf import settings
from django.db import close_old_connections
from rest_framework.exceptions import ValidationError
from apps.agency.models import Agency, Job, CandidateGatheringSession, Candidate, Activity, CandidateProfile
from apps.accounts.models import User

logger = logging.getLogger(__name__)


def create_candidate_gathering_session(agency: Agency, job: Job, user: User) -> CandidateGatheringSession:
    """
    Creates and saves a CandidateGatheringSession object.
    """
    return CandidateGatheringSession.objects.create(
        agency=agency,
        job=job,
        user=user,
        status='pending'
    )


def trigger_candidate_gathering(session: CandidateGatheringSession) -> None:
    """
    Unified entry point to trigger candidate gathering based on the configured provider.
    Toggled via settings.CANDIDATE_GATHERING_PROVIDER ('n8n' or 'apify').
    """
    provider = getattr(settings, 'CANDIDATE_GATHERING_PROVIDER', 'n8n').lower()

    if provider == 'apify':
        trigger_apify_candidate_gathering(session)
    else:
        trigger_n8n_candidate_gathering(session)


def trigger_n8n_candidate_gathering(session: CandidateGatheringSession) -> None:
    """
    Triggers the n8n candidate gathering workflow via webhook.
    """
    webhook_url = getattr(settings, 'N8N_CANDIDATE_WEBHOOK_URL', None) or getattr(settings, 'N8N_WEBHOOK_URL', None)
    if not webhook_url:
        session.status = 'failed'
        session.save(update_fields=['status'])
        logger.error("Neither N8N_CANDIDATE_WEBHOOK_URL nor N8N_WEBHOOK_URL is configured in settings.")
        raise ValidationError({"detail": "Candidate gathering service is not configured (missing webhook URL)."})

    payload = {
        'session_id': str(session.id),
        'agency_id': session.agency.id,
        'user_id': str(session.user.id),
        'job_id': session.job.id,
        'job_title': session.job.title,
        'job_description': session.job.description,
        'location': session.job.location,
        'experience_required': session.job.experince_required,
        'skills': session.job.skills,
        'job_type': session.job.job_type
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
        logger.exception("Failed to send candidate gathering webhook request to n8n.")
        raise ValidationError({"detail": f"Failed to initiate candidate gathering with n8n workflow: {str(e)}"})


def trigger_apify_candidate_gathering(session: CandidateGatheringSession) -> None:
    """
    Triggers backend candidate gathering via Apify in a background thread.
    """
    api_key = getattr(settings, 'APIFY_API_KEY', '')
    if not api_key:
        session.status = 'failed'
        session.save(update_fields=['status'])
        logger.error("APIFY_API_KEY is not configured in settings.")
        raise ValidationError({"detail": "Candidate gathering service is not configured (missing APIFY_API_KEY)."})

    session.status = 'processing'
    session.save(update_fields=['status'])

    thread = threading.Thread(
        target=_process_apify_candidate_gathering_in_background,
        args=(str(session.id), session.agency.id, session.job.id, str(session.user.id) if session.user else None)
    )
    thread.daemon = True
    thread.start()


def _normalize_candidate_from_profile_item(item: dict, default_skills: list = None) -> dict:
    """
    Normalizes a deep LinkedIn profile item from harvestapi/linkedin-profile-scraper.
    Extracts full name, headline, summary, positions/work experience, education, skills, location, and contact.
    """
    first_name = item.get('firstName') or item.get('first_name') or ''
    last_name = item.get('lastName') or item.get('last_name') or ''
    full_name_direct = f"{first_name} {last_name}".strip() if first_name or last_name else ''
    raw_name = item.get('fullName') or item.get('name') or item.get('full_name') or full_name_direct

    headline = item.get('headline') or item.get('position') or item.get('occupation') or item.get('current_title') or ''
    summary = item.get('summary') or item.get('about') or item.get('description') or ''
    url = item.get('linkedinUrl') or item.get('profileUrl') or item.get('url') or ''
    
    # Extract email from emails list or direct field
    raw_emails = item.get('emails') or []
    email = None
    if isinstance(raw_emails, list) and raw_emails:
        email = raw_emails[0]
    elif isinstance(raw_emails, str) and '@' in raw_emails:
        email = raw_emails
    else:
        email = item.get('email') or item.get('mail') or None

    # Check if candidate listed their email in their summary / bio
    if not email and summary:
        found_emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', summary)
        if found_emails:
            email = found_emails[0]

    phone = item.get('phone') or item.get('phoneNumber') or ''

    # Clean location
    raw_loc = item.get('location') or item.get('geoCountryName') or item.get('city') or ''
    if isinstance(raw_loc, dict):
        raw_loc = raw_loc.get('name') or raw_loc.get('city') or ''
    location = str(raw_loc).strip() if raw_loc else ""

    # Parse work experience history
    raw_positions = item.get('positions') or item.get('experience') or item.get('experiences') or []
    experience_history = []
    total_exp_years = 0.0

    if isinstance(raw_positions, list):
        for pos in raw_positions:
            if isinstance(pos, dict):
                comp_name = pos.get('companyName') or pos.get('company') or pos.get('title') or ''
                pos_title = pos.get('title') or pos.get('position') or ''
                dur_str = pos.get('duration') or pos.get('durationFormatted') or ''
                desc = pos.get('description') or ''
                experience_history.append({
                    'company': comp_name,
                    'title': pos_title,
                    'duration': dur_str,
                    'description': desc[:300] if desc else ''
                })

        # Calculate or extract total years
        total_exp_years = item.get('totalExperienceInYears') or len(experience_history) * 1.5

    # Parse education history
    raw_education = item.get('educations') or item.get('education') or []
    education_history = []
    if isinstance(raw_education, list):
        for edu in raw_education:
            if isinstance(edu, dict):
                school = edu.get('schoolName') or edu.get('school') or edu.get('institution') or ''
                deg = edu.get('degreeName') or edu.get('degree') or ''
                field = edu.get('fieldOfStudy') or edu.get('field_of_study') or ''
                education_history.append({
                    'school': school,
                    'degree': deg,
                    'field_of_study': field
                })

    # Parse skills
    extracted_skills = []
    raw_skills = item.get('skills') or []
    if isinstance(raw_skills, list):
        for s in raw_skills:
            if isinstance(s, str) and s.strip():
                extracted_skills.append(s.strip())
            elif isinstance(s, dict) and s.get('name'):
                extracted_skills.append(s['name'].strip())

    if not extracted_skills and default_skills:
        extracted_skills = default_skills

    # Name sanity check
    if not raw_name or len(raw_name.split()) < 2:
        return None

    return {
        'name': raw_name[:100],
        'email': email if email and '@' in email else None,
        'phone': phone[:50] if phone else "",
        'location': location[:100] if location else "",
        'experience': int(total_exp_years) if total_exp_years else 0,
        'skills': extracted_skills,
        'snippet': summary[:1000] if summary else "",
        'title': headline[:255] if headline else "",
        'source_url': url,
        'experience_history': experience_history,
        'education_history': education_history,
        'raw_profile_json': item
    }


def _normalize_candidate_from_item(item: dict, default_skills: list = None) -> dict:
    """
    Normalizes a raw search result scraped item into a candidate dictionary.
    Strictly filters out non-human profile data, posts, job listings, articles, and guide pages.
    """
    first_name = item.get('firstName') or item.get('first_name') or ''
    last_name = item.get('lastName') or item.get('last_name') or ''
    full_name_direct = f"{first_name} {last_name}".strip() if first_name or last_name else ''
    raw_name = item.get('name') or item.get('full_name') or item.get('fullName') or full_name_direct

    title = item.get('headline') or item.get('occupation') or item.get('current_title') or item.get('title') or ''
    snippet = item.get('summary') or item.get('about') or item.get('description') or item.get('snippet') or item.get('text') or ''
    url = item.get('profileUrl') or item.get('linkedinUrl') or item.get('profile_url') or item.get('url') or item.get('link') or ''
    email = item.get('email') or item.get('mail') or None
    phone = item.get('phone') or item.get('phoneNumber') or ''

    # Filter non-profiles
    junk_patterns = [
        'resume example', 'resume template', 'guide for', 'job description',
        'top 10', 'interview question', 'salary for', 'salaries', 'hiring guide',
        'best resume', 'how to write', 'prospective', 'overview', 'developer resume',
        'engineer resume', 'sample resume', 'cv template', "'s post", "’s post",
        "jobs in", "developer jobs", "engineer jobs", "employment", "openings",
        "we are hiring", "job alert"
    ]
    combined_check = f"{title} {raw_name}".lower()
    if any(pattern in combined_check for pattern in junk_patterns):
        logger.debug(f"[CandidateGathering] Item '{title}' matched junk pattern, skipping.")
        return None

    # Clean name from title if raw name is not found
    if not raw_name and title:
        cleaned_title = re.sub(r'(?i)\s*[-|–|—|:]\s*(linkedin|github|resume|cv|profile|portfolio).*$', '', title)
        parts = re.split(r'\s*[-|–|—|@|\|]\s*', cleaned_title)
        name_candidate = parts[0].strip() if parts else ''
        name_candidate = re.sub(r'[^\w\s\.\'-]', '', name_candidate).strip()
        words = name_candidate.split()
        if 1 <= len(words) <= 4 and not any(char.isdigit() for char in name_candidate):
            raw_name = name_candidate

    if not raw_name or len(raw_name.split()) < 2:
        return None

    # Discard non-person indicators
    name_lower = raw_name.lower()
    invalid_name_indicators = [
        'resume', 'guide', 'template', 'prospective', 'developer', 'engineer',
        'specialist', 'candidate', 'sample', 'example', 'jobs', 'salary', 'hiring',
        'salaries', 'top 10', 'overview', 'post', 'alert', 'employment'
    ]
    if any(ind in name_lower for ind in invalid_name_indicators):
        return None

    # Extract email from snippet if present
    if not email and snippet:
        emails_found = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', snippet)
        if emails_found:
            email = emails_found[0]

    # Extract experience
    experience = item.get('totalExperienceInYears') or item.get('experience') or item.get('total_experience_years')
    if experience is None:
        exp_match = re.search(r'(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:experience|exp)', f"{title} {snippet}", re.IGNORECASE)
        experience = int(exp_match.group(1)) if exp_match else 0

    # Extract location
    candidate_loc = ""
    direct_loc = item.get('location') or item.get('geoCountryName') or item.get('city')
    if direct_loc and isinstance(direct_loc, str):
        candidate_loc = direct_loc.strip()
    else:
        loc_match = re.search(r'([A-Za-z\s]+,\s*(?:[A-Za-z\s]{2,}|[A-Z]{2}))(?:\.|\s|·|-|,|\n)', snippet)
        if loc_match:
            candidate_loc = loc_match.group(1).strip()

    skills = item.get('skills') or default_skills or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(',') if s.strip()]

    return {
        'name': raw_name[:100],
        'email': email if email and '@' in email else None,
        'phone': phone[:50] if phone else "",
        'location': candidate_loc[:100] if candidate_loc else "",
        'experience': int(experience) if experience is not None else 0,
        'skills': skills,
        'snippet': snippet,
        'title': title,
        'source_url': url,
        'experience_history': [],
        'education_history': []
    }


def _process_apify_candidate_gathering_in_background(session_id: str, agency_id: int, job_id: int, user_id: str = None) -> None:
    """
    Background worker implementing a Two-Stage candidate gathering pipeline:
    Stage 1: Google Search Scraper discovers candidate LinkedIn profile URLs.
    Stage 2: LinkedIn Profile Scraper (harvestapi) fetches rich work history, education, skills, and contact details.
    Stage 3: AI scoring, matching, and candidate ingestion (with nullable emails, no fake @temp.com).
    """
    from apps.agency.utils.apify_client import ApifyClient

    try:
        session = CandidateGatheringSession.objects.get(id=session_id)
        agency = Agency.objects.get(id=agency_id)
        job = Job.objects.get(id=job_id, agency=agency)
        user = User.objects.get(id=user_id) if user_id else None

        client = ApifyClient()

        # -------------------------------------------------------------
        # STAGE 1: Discover Candidate LinkedIn Profile URLs via Google Search Scraper
        # -------------------------------------------------------------
        loc_str = job.location or ''
        search_query = f'site:linkedin.com/in/ "{job.title}" {loc_str}'.strip()
        search_actor_id = getattr(settings, 'APIFY_CANDIDATE_ACTOR_ID', 'apify/google-search-scraper')

        logger.info(
            f"[CandidateGathering] Stage 1: Starting Google Discovery. "
            f"Job ID={job.id} ('{job.title}'), Query='{search_query}'"
        )

        actor_input = {
            "queries": search_query,
            "maxPagesPerQuery": 1,
            "resultsPerPage": 15
        }
        dataset_items = client.run_actor(actor_id=search_actor_id, run_input=actor_input, timeout_secs=180)

        raw_search_items = []
        for item in dataset_items:
            if "organicResults" in item and isinstance(item["organicResults"], list):
                raw_search_items.extend(item["organicResults"])
            else:
                raw_search_items.append(item)

        logger.info(f"[CandidateGathering] Stage 1 returned {len(raw_search_items)} search items.")

        # Collect and filter genuine LinkedIn profile URLs
        linkedin_urls = []
        stage1_candidates_map = {}

        for item in raw_search_items:
            cand_dict = _normalize_candidate_from_item(item, default_skills=job.skills if isinstance(job.skills, list) else [])
            if cand_dict and cand_dict.get('source_url'):
                url = cand_dict['source_url'].split('?')[0].rstrip('/')
                if 'linkedin.com/in/' in url and url not in linkedin_urls:
                    linkedin_urls.append(url)
                    stage1_candidates_map[url] = cand_dict

        logger.info(f"[CandidateGathering] Stage 1 extracted {len(linkedin_urls)} valid candidate LinkedIn URLs.")

        # -------------------------------------------------------------
        # STAGE 2: Deep Profile Enrichment via LinkedIn Profile Scraper
        # -------------------------------------------------------------
        profile_actor_id = getattr(settings, 'APIFY_LINKEDIN_PROFILE_ACTOR_ID', 'harvestapi/linkedin-profile-scraper')
        candidates_data = []

        if linkedin_urls and profile_actor_id:
            try:
                logger.info(f"[CandidateGathering] Stage 2: Running profile scraper '{profile_actor_id}' for {len(linkedin_urls)} URLs.")
                profile_input = {"queries": linkedin_urls}
                profile_dataset = client.run_actor(actor_id=profile_actor_id, run_input=profile_input, timeout_secs=180)
                
                if profile_dataset and isinstance(profile_dataset, list):
                    logger.info(f"[CandidateGathering] Stage 2: Received {len(profile_dataset)} full profile records from Apify.")
                    for p_item in profile_dataset:
                        normalized_p = _normalize_candidate_from_profile_item(
                            p_item, default_skills=job.skills if isinstance(job.skills, list) else []
                        )
                        if normalized_p and normalized_p.get('name'):
                            candidates_data.append(normalized_p)

            except Exception as stage2_err:
                logger.warning(f"[CandidateGathering] Stage 2 profile scraping failed ({stage2_err}), falling back to Stage 1 search results.")

        # Fallback to Stage 1 data if Stage 2 produced no candidates
        if not candidates_data and stage1_candidates_map:
            logger.info("[CandidateGathering] Using Stage 1 parsed candidates as fallback.")
            candidates_data = list(stage1_candidates_map.values())

        logger.info(f"[CandidateGathering] Final validated candidates count: {len(candidates_data)}.")

        if not candidates_data:
            logger.info(f"[CandidateGathering] No candidates found for job '{job.title}' (session {session_id}).")
            session.status = 'completed'
            session.save(update_fields=['status'])
            if user:
                from apps.notifications.services.notifications import create_notification
                try:
                    create_notification(
                        user=user,
                        title="Candidate Gathering Complete",
                        message=f"Candidate gathering completed for job '{job.title}'. No new candidate profiles were found matching criteria.",
                        notification_type="candidate_gathering_complete",
                        source={"session_id": str(session_id), "job_id": job.id}
                    )
                except Exception:
                    pass
            return

        # -------------------------------------------------------------
        # STAGE 3: Ingest Shell Profiles & Dispatch AI Processing
        # -------------------------------------------------------------
        candidate_ids = []
        for cand_data in candidates_data:
            fallback_name = cand_data.get('name')
            email = cand_data.get('email') or None
            phone = cand_data.get('phone') or ""

            db_profile = None
            if email:
                db_profile = CandidateProfile.objects.filter(agency=agency, email=email).first()
            if not db_profile and phone:
                db_profile = CandidateProfile.objects.filter(agency=agency, phone=phone).first()
            if not db_profile and fallback_name:
                db_profile = CandidateProfile.objects.filter(agency=agency, name=fallback_name, email__isnull=True).first()

            if not db_profile:
                db_profile = CandidateProfile.objects.create(
                    agency=agency,
                    name=fallback_name,
                    email=email,  # Nullable, NO fake @temp.com!
                    phone=phone,
                    location=cand_data.get('location') or "",
                    experience=cand_data.get('experience') or 0,
                    skills=cand_data.get('skills') or [],
                    current_salary="",
                    expected_salary="",
                    ai_extracted_raw_json=cand_data
                )

            cand = Candidate.objects.create(
                agency=agency,
                job=job,
                profile=db_profile,
                status='new',
                is_processing=True
            )
            candidate_ids.append(cand.id)

        # Trigger background AI parsing and scoring batch
        _process_gathered_candidates_batch_in_background(
            session_id=str(session.id),
            agency_id=agency.id,
            job_id=job.id,
            user_id=user.id if user else None,
            candidates_data_list=candidates_data,
            candidate_ids=candidate_ids
        )

    except Exception as e:
        logger.exception(f"Error in Apify candidate gathering background task for session {session_id}: {e}")
        try:
            CandidateGatheringSession.objects.filter(id=session_id).update(status='failed')
        except Exception:
            pass
    finally:
        close_old_connections()


def _process_gathered_candidates_batch_in_background(
    session_id, agency_id, job_id, user_id, candidates_data_list, candidate_ids
):
    """
    Processes a batch of gathered candidates in a background thread.
    Uses rich work history and AI parsing, scoring, and analysis.
    """
    from apps.ai.candidate_parser import CandidateParser
    from apps.ai.models.candidate import CandidateProfile as AICandidateProfile
    from apps.agency.services.candidates import process_candidate_ai_match
    
    try:
        agency = Agency.objects.get(id=agency_id)
        job = Job.objects.get(id=job_id)
        user = User.objects.get(id=user_id) if user_id else None

        processed_count = 0

        for cand_id, cand_data in zip(candidate_ids, candidates_data_list):
            try:
                candidate = Candidate.objects.get(id=cand_id)

                # Build rich candidate bio from Stage 2 enriched profile
                bio_lines = [
                    f"Candidate Full Name: {cand_data.get('name')}",
                    f"Headline / Current Role: {cand_data.get('title') or job.title}",
                    f"Location: {cand_data.get('location') or ''}",
                    f"Total Experience: {cand_data.get('experience', 0)} years",
                    f"Technical Skills: {', '.join(cand_data.get('skills', [])) if isinstance(cand_data.get('skills'), list) else cand_data.get('skills')}",
                    f"LinkedIn Profile: {cand_data.get('source_url', '')}",
                ]

                if cand_data.get('experience_history'):
                    bio_lines.append("\nWork Experience History:")
                    for exp in cand_data['experience_history']:
                        comp = exp.get('company', '')
                        pos = exp.get('title', '')
                        dur = exp.get('duration', '')
                        desc = exp.get('description', '')
                        bio_lines.append(f"- {pos} at {comp} ({dur}) {': ' + desc if desc else ''}")

                if cand_data.get('education_history'):
                    bio_lines.append("\nEducation History:")
                    for edu in cand_data['education_history']:
                        deg = edu.get('degree', '')
                        inst = edu.get('school', '')
                        field = edu.get('field_of_study', '')
                        bio_lines.append(f"- {deg} in {field} from {inst}".strip())

                if cand_data.get('snippet'):
                    bio_lines.append(f"\nAbout & Summary:\n{cand_data.get('snippet')}")

                candidate_bio = "\n".join(bio_lines)

                # 1. Parse using LLM CandidateParser
                profile = None
                raw_json = None
                try:
                    parser = CandidateParser()
                    profile = parser.parse_candidate(candidate_bio)
                    if profile:
                        raw_json = profile.model_dump()
                except Exception as e:
                    logger.error(f"Failed to parse candidate JSON using LLM for candidate {cand_id}: {e}")

                # Strict Human Check
                parsed_name = (profile.full_name if profile else cand_data.get('name') or "").strip()
                name_lower = parsed_name.lower()
                fake_indicators = [
                    'prospective', 'candidate', 'developer', 'engineer', 'resume',
                    'example', 'guide', 'template', 'specialist', 'sample',
                    'salary', 'hiring', 'overview', 'top 10', 'how to', 'best',
                    'post', 'employment', 'alert', 'jobs'
                ]
                if not parsed_name or any(ind in name_lower for ind in fake_indicators) or len(parsed_name.split()) < 2:
                    logger.warning(f"[CandidateGathering] Discarding non-human candidate data: ID {cand_id} ('{parsed_name}')")
                    temp_prof = candidate.profile
                    candidate.delete()
                    if temp_prof and not Candidate.objects.filter(profile=temp_prof).exists():
                        temp_prof.delete()
                    continue

                # Fallback profile
                if not profile:
                    profile = AICandidateProfile(
                        full_name=parsed_name,
                        email=cand_data.get('email') or None,
                        phone=cand_data.get('phone') or "",
                        location=cand_data.get('location') or "",
                        total_experience_years=float(cand_data.get('experience') or 0.0),
                        technical_skills=cand_data.get('skills') or []
                    )
                    raw_json = profile.model_dump()

                # Update or merge CandidateProfile
                email = profile.email or cand_data.get('email') or None
                phone = profile.phone or cand_data.get('phone') or ""

                db_profile = None
                if email:
                    db_profile = CandidateProfile.objects.filter(agency=agency, email=email).exclude(id=candidate.profile.id).first()
                if not db_profile and phone:
                    db_profile = CandidateProfile.objects.filter(agency=agency, phone=phone).exclude(id=candidate.profile.id).first()

                temp_profile = candidate.profile

                if db_profile:
                    candidate.profile = db_profile
                    candidate.save()
                    if temp_profile:
                        temp_profile.delete()
                else:
                    db_profile = temp_profile

                # Update db_profile fields with parsed details
                db_profile.name = profile.full_name or db_profile.name
                db_profile.email = email  # Real email or None
                db_profile.phone = phone or db_profile.phone or ""
                db_profile.location = profile.location or db_profile.location or ""
                db_profile.experience = int(profile.total_experience_years) if profile.total_experience_years is not None else 0
                db_profile.skills = profile.technical_skills or []
                db_profile.current_salary = profile.current_salary or ""
                db_profile.expected_salary = profile.expected_salary or ""
                db_profile.ai_extracted_raw_json = raw_json
                db_profile.save()

                # Check for existing candidate application and handle versioning
                from apps.agency.services.candidates import handle_candidate_versioning
                candidate = handle_candidate_versioning(agency, job, db_profile, candidate)

                # 3. Trigger AI scoring & analysis
                process_candidate_ai_match(candidate, profile, job, agency)

                candidate.is_processing = False
                candidate.save()

                # 4. Log candidate creation activity
                Activity.objects.create(
                    model='candidate',
                    model_id=candidate.id,
                    agency=agency,
                    user=user,
                    summary=f"Gathered and enriched candidate profile for {candidate.name}"
                )

                processed_count += 1
            except Exception as single_err:
                logger.error(f"Error processing gathered candidate {cand_id}: {single_err}")
                try:
                    Candidate.objects.filter(id=cand_id).update(is_processing=False)
                except Exception:
                    pass

        # 5. Finalize Session status
        if session_id:
            try:
                session = CandidateGatheringSession.objects.get(id=session_id)
                session.status = 'completed'
                session.save(update_fields=['status'])
            except CandidateGatheringSession.DoesNotExist:
                pass

        # 6. Send notification to recruiter
        if user:
            from apps.notifications.services.notifications import create_notification
            try:
                create_notification(
                    user=user,
                    title="Candidate Gathering Complete",
                    message=f"Candidate gathering completed. {processed_count} enriched candidates processed successfully for job '{job.title}'.",
                    notification_type="candidate_gathering_complete",
                    source={"session_id": str(session_id) if session_id else None, "job_id": job.id}
                )
            except Exception as notification_err:
                logger.error(f"Failed to send candidate gathering notification: {notification_err}")

    except Exception as outer_err:
        logger.error(f"Error in background candidate gathering processing task: {outer_err}")
        if session_id:
            try:
                CandidateGatheringSession.objects.filter(id=session_id).update(status='failed')
            except Exception:
                pass
    finally:
        close_old_connections()


def trigger_gathered_candidates_processing(
    session_id, agency_id, job_id, user_id, candidates_data_list, candidate_ids
) -> None:
    """
    Spawns a background thread to process the batch of gathered candidates.
    """
    thread = threading.Thread(
        target=_process_gathered_candidates_batch_in_background,
        args=(session_id, agency_id, job_id, user_id, candidates_data_list, candidate_ids)
    )
    thread.daemon = True
    thread.start()
