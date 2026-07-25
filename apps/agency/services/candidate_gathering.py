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


def _process_gathered_candidates_batch_in_background(
    session_id, agency_id, job_id, user_id, candidates_data_list, candidate_ids
):
    """
    Processes a batch of gathered candidates in a background thread.
    Uses AI parsing, scoring, and analysis, then stores them and notifies the recruiter.
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
                candidate_json_str = json.dumps(cand_data, indent=2)

                # 1. Parse using LLM CandidateParser
                profile = None
                raw_json = None
                try:
                    parser = CandidateParser()
                    profile = parser.parse_candidate(candidate_json_str)
                    if profile:
                        raw_json = profile.model_dump()
                except Exception as e:
                    logger.error(f"Failed to parse candidate JSON using LLM for candidate {cand_id}: {e}")

                # Fallback to default profile if LLM parsing failed
                if not profile:
                    fallback_name = cand_data.get('name') or cand_data.get('full_name') or candidate.name
                    profile = CandidateProfile(
                        full_name=fallback_name,
                        email=cand_data.get('email'),
                        phone=cand_data.get('phone'),
                        location=cand_data.get('location'),
                        total_experience_years=float(cand_data.get('experience') or cand_data.get('total_experience_years') or 0.0),
                        technical_skills=cand_data.get('skills') or []
                    )
                    raw_json = profile.model_dump()

                # 2. Update candidate fields
                candidate.name = profile.full_name or candidate.name
                candidate.email = profile.email or cand_data.get('email') or ""
                candidate.phone = profile.phone or cand_data.get('phone') or ""
                candidate.location = profile.location or cand_data.get('location') or ""
                candidate.experience = int(profile.total_experience_years) if profile.total_experience_years is not None else 0
                candidate.skills = profile.technical_skills or []
                candidate.current_salary = profile.current_salary or ""
                candidate.expected_salary = profile.expected_salary or ""
                candidate.ai_extracted_raw_json = raw_json
                candidate.save()

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
