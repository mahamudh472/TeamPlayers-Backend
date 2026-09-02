import json
import logging
import requests
import threading
from django.conf import settings
from django.db import close_old_connections
from rest_framework.exceptions import ValidationError
from apps.agency.models import Agency, Job, CandidateGatheringSession, Candidate, Activity
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


def _normalize_candidate_from_item(item: dict, default_skills: list = None) -> dict:
    """
    Normalizes a raw scraped item into a candidate dictionary.
    Strictly filters out non-human profile data, articles, and guide pages.
    """
    import re

    # 1. Direct fields from dedicated LinkedIn scrapers
    first_name = item.get('firstName') or item.get('first_name') or ''
    last_name = item.get('lastName') or item.get('last_name') or ''
    full_name_direct = f"{first_name} {last_name}".strip() if first_name or last_name else ''
    raw_name = item.get('name') or item.get('full_name') or item.get('fullName') or full_name_direct

    title = item.get('headline') or item.get('occupation') or item.get('current_title') or item.get('title') or ''
    snippet = item.get('summary') or item.get('about') or item.get('description') or item.get('snippet') or item.get('text') or ''
    url = item.get('profileUrl') or item.get('linkedinUrl') or item.get('profile_url') or item.get('url') or item.get('link') or ''
    email = item.get('email') or item.get('mail') or ''
    phone = item.get('phone') or item.get('phoneNumber') or ''

    # Filter non-profiles (e.g. "Resume Examples & Guide", "Job Description", etc.)
    junk_patterns = [
        'resume example', 'resume template', 'guide for', 'job description',
        'top 10', 'interview question', 'salary for', 'salaries', 'hiring guide',
        'best resume', 'how to write', 'prospective', 'overview', 'developer resume',
        'engineer resume', 'sample resume', 'cv template'
    ]
    combined_check = f"{title} {raw_name}".lower()
    if any(pattern in combined_check for pattern in junk_patterns):
        return None

    # Clean name from title/snippets if raw name is not found
    if not raw_name:
        if title:
            # Common patterns in LinkedIn profile searches: "Firstname Lastname - Senior Python Developer | LinkedIn"
            cleaned_title = re.sub(r'(?i)\s*[-|–|—|:]\s*(linkedin|github|resume|cv|profile|portfolio).*$', '', title)
            parts = re.split(r'\s*[-|–|—|@|\|]\s*', cleaned_title)
            name_candidate = parts[0].strip() if parts else ''
            
            # Ensure the extracted name candidate looks like a genuine human name (1 to 4 words, no digits)
            words = name_candidate.split()
            if 1 <= len(words) <= 4 and not any(char.isdigit() for char in name_candidate):
                raw_name = name_candidate

    if not raw_name:
        return None

    # Discard if name itself contains non-person words
    name_lower = raw_name.lower()
    invalid_name_indicators = [
        'resume', 'guide', 'template', 'prospective', 'developer', 'engineer',
        'specialist', 'candidate', 'sample', 'example', 'jobs', 'salary', 'hiring',
        'salaries', 'top 10', 'overview'
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
        if exp_match:
            try:
                experience = int(exp_match.group(1))
            except (ValueError, TypeError):
                experience = 0
        else:
            experience = 0

    # Extract location from direct field or snippet ONLY if explicitly found (DO NOT default to job location)
    candidate_loc = ""
    direct_loc = item.get('location') or item.get('geoCountryName') or item.get('city')
    if direct_loc and isinstance(direct_loc, str):
        candidate_loc = direct_loc.strip()
    else:
        loc_match = re.search(r'([A-Za-z\s]+,\s*(?:[A-Za-z\s]{2,}|[A-Z]{2}))(?:\.|\s|·|-|,|\n)', snippet)
        if loc_match:
            candidate_loc = loc_match.group(1).strip()

    tech_and_junk = ['experience', 'designing', 'skills', 'engineer', 'developer', 'looking', 'years', 'django', 'fastapi', 'python', 'react', 'node', 'aws', 'sql', 'api']
    if any(bad_word in candidate_loc.lower() for bad_word in tech_and_junk):
        candidate_loc = ""

    skills = item.get('skills') or default_skills or []
    if isinstance(skills, str):
        skills = [s.strip() for s in skills.split(',') if s.strip()]

    return {
        'name': raw_name[:255],
        'email': email,
        'phone': phone,
        'location': candidate_loc[:255] if candidate_loc else "",
        'experience': int(experience) if experience is not None else 0,
        'skills': skills,
        'snippet': snippet,
        'title': title,
        'source_url': url
    }


def _process_apify_candidate_gathering_in_background(session_id: str, agency_id: int, job_id: int, user_id: str = None) -> None:
    """
    Background worker that runs the Apify candidate scraper, creates shell candidates,
    and dispatches to the AI parsing and scoring pipeline.
    """
    import uuid
    from urllib.parse import quote_plus
    from apps.agency.utils.apify_client import ApifyClient
    from apps.agency.models import CandidateProfile

    try:
        session = CandidateGatheringSession.objects.get(id=session_id)
        agency = Agency.objects.get(id=agency_id)
        job = Job.objects.get(id=job_id, agency=agency)
        user = User.objects.get(id=user_id) if user_id else None

        actor_id = getattr(settings, 'APIFY_CANDIDATE_ACTOR_ID', 'apify/google-search-scraper')
        client = ApifyClient()

        # Build targeted query for LinkedIn candidate profiles
        loc_str = job.location or ''
        if isinstance(job.skills, list) and job.skills:
            top_skills = " ".join([f'"{s}"' for s in job.skills[:2]])
        else:
            top_skills = ""

        search_text = f"{job.title} {top_skills} {loc_str}".strip()
        google_query = f'site:linkedin.com/in/ "{job.title}" {top_skills} {loc_str}'

        # Dynamically format payload based on actor requirements
        if "google-search-scraper" in actor_id:
            actor_input = {
                "queries": google_query.strip(),
                "maxPagesPerQuery": 1,
                "resultsPerPage": 15
            }
        elif "harvestapi" in actor_id:
            actor_input = {
                "searchQuery": search_text,
                "locations": [job.location] if job.location else [],
                "maxItems": 15
            }
        elif "curious_coder" in actor_id or "people-search" in actor_id:
            actor_input = {
                "searchUrl": f"https://www.linkedin.com/search/results/people/?keywords={quote_plus(search_text)}",
                "maxItems": 15
            }
        else:
            actor_input = {
                "searchQuery": search_text,
                "job_title": job.title,
                "skills": job.skills,
                "location": job.location,
                "queries": google_query.strip(),
                "maxItems": 15
            }

        dataset_items = client.run_actor(actor_id=actor_id, run_input=actor_input, timeout_secs=180)

        # Flatten organicResults if returned by google-search-scraper
        raw_items = []
        for item in dataset_items:
            if "organicResults" in item and isinstance(item["organicResults"], list):
                raw_items.extend(item["organicResults"])
            else:
                raw_items.append(item)

        candidates_data = []
        for item in raw_items:
            cand_dict = _normalize_candidate_from_item(
                item=item,
                default_skills=job.skills if isinstance(job.skills, list) else []
            )
            if cand_dict and cand_dict.get('name'):
                candidates_data.append(cand_dict)

        if not candidates_data:
            logger.info(f"No valid candidate profiles found via Apify for job {job.title} (session {session_id}).")
            session.status = 'completed'
            session.save(update_fields=['status'])
            if user:
                from apps.notifications.services.notifications import create_notification
                try:
                    create_notification(
                        user=user,
                        title="Candidate Gathering Complete",
                        message=f"Candidate gathering completed for job '{job.title}'. No new candidate profiles were found matching the search criteria.",
                        notification_type="candidate_gathering_complete",
                        source={"session_id": str(session_id), "job_id": job.id}
                    )
                except Exception:
                    pass
            return

        # Create shell candidates and profiles
        candidate_ids = []
        for cand_data in candidates_data:
            fallback_name = cand_data.get('name')
            email = cand_data.get('email') or ""
            phone = cand_data.get('phone') or ""

            db_profile = None
            if email:
                db_profile = CandidateProfile.objects.filter(agency=agency, email=email).first()
            if not db_profile and phone:
                db_profile = CandidateProfile.objects.filter(agency=agency, phone=phone).first()

            if not db_profile:
                db_profile = CandidateProfile.objects.create(
                    agency=agency,
                    name=fallback_name,
                    email=email or f"gathered-{uuid.uuid4().hex[:10]}@temp.com",
                    phone=phone or "",
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

        # Trigger background processing for batch
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
    Uses AI parsing, scoring, and analysis, then stores them and notifies the recruiter.
    Strictly verifies and discards any non-human candidate data.
    """
    from apps.ai.candidate_parser import CandidateParser
    from apps.ai.models.candidate import CandidateProfile
    from apps.agency.services.candidates import process_candidate_ai_match
    
    try:
        agency = Agency.objects.get(id=agency_id)
        job = Job.objects.get(id=job_id)
        user = User.objects.get(id=user_id) if user_id else None

        processed_count = 0

        for cand_id, cand_data in zip(candidate_ids, candidates_data_list):
            try:
                candidate = Candidate.objects.get(id=cand_id)
                candidate_bio = (
                    f"Candidate Full Name: {cand_data.get('name')}\n"
                    f"Current / Target Role: {cand_data.get('title') or job.title}\n"
                    f"Location: {cand_data.get('location') or ''}\n"
                    f"Total Experience: {cand_data.get('experience', 0)} years\n"
                    f"Technical Skills: {', '.join(cand_data.get('skills', [])) if isinstance(cand_data.get('skills'), list) else cand_data.get('skills')}\n"
                    f"LinkedIn Profile: {cand_data.get('source_url', '')}\n"
                    f"Candidate Bio and Summary:\n{cand_data.get('snippet', '')}\n"
                )

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

                # Strict Human Check: If parsed name looks fake/non-human, discard and delete object
                parsed_name = (profile.full_name if profile else cand_data.get('name') or "").strip()
                name_lower = parsed_name.lower()
                fake_indicators = [
                    'prospective', 'candidate', 'developer', 'engineer', 'resume',
                    'example', 'guide', 'template', 'specialist', 'sample',
                    'salary', 'hiring', 'overview', 'top 10', 'how to', 'best'
                ]
                if not parsed_name or any(ind in name_lower for ind in fake_indicators) or len(parsed_name.split()) < 2:
                    logger.info(f"Discarding and deleting non-human candidate data: ID {cand_id} ('{parsed_name}')")
                    temp_prof = candidate.profile
                    candidate.delete()
                    if temp_prof and not Candidate.objects.filter(profile=temp_prof).exists():
                        temp_prof.delete()
                    continue

                # Fallback to default profile if LLM parsing failed
                if not profile:
                    profile = CandidateProfile(
                        full_name=parsed_name,
                        email=cand_data.get('email'),
                        phone=cand_data.get('phone'),
                        location=cand_data.get('location') or "",
                        total_experience_years=float(cand_data.get('experience') or 0.0),
                        technical_skills=cand_data.get('skills') or []
                    )
                    raw_json = profile.model_dump()

                # Update or merge CandidateProfile
                from apps.agency.models import CandidateProfile
                email = profile.email or ""
                phone = profile.phone or ""

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
                db_profile.email = profile.email or db_profile.email
                db_profile.phone = profile.phone or db_profile.phone or ""
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
                    summary=f"Gathered and processed candidate profile for {candidate.name}"
                )

                processed_count += 1
            except Exception as single_err:
                logger.error(f"Error processing gathered candidate {cand_id}: {single_err}")
                # Ensure the candidate doesn't get stuck in processing
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

        # 6. Send notification to the initiating user
        if user:
            from apps.notifications.services.notifications import create_notification
            try:
                create_notification(
                    user=user,
                    title="Candidate Gathering Complete",
                    message=f"Candidate gathering completed. {processed_count} candidates processed successfully for job '{job.title}'.",
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
