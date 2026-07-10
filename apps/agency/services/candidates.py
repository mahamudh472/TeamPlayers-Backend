from django.db.models import Q, QuerySet, Count
from apps.agency.models import Agency, Candidate, Note, Activity
from apps.accounts.models import User
from rest_framework.exceptions import NotFound

def get_agency_candidates(agency: Agency, search_query: str = None) -> QuerySet[Candidate]:
    """
    Returns candidates for the agency, optionally filtered by a search query.
    Performs case-insensitive checks on name, email, location, and job title.
    """
    queryset = Candidate.objects.filter(agency=agency).select_related('job').prefetch_related('ai_analysis').order_by('-applied_at')
    if search_query:
        queryset = queryset.filter(
            Q(name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(job__title__icontains=search_query)
        )
    return queryset

def get_agency_candidate_by_id(agency: Agency, candidate_id: int) -> Candidate:
    """
    Returns a single candidate for the agency, or raises NotFound.
    """
    try:
        return Candidate.objects.select_related('job').prefetch_related('ai_analysis').get(agency=agency, id=candidate_id)
    except (Candidate.DoesNotExist, ValueError):
        raise NotFound("Candidate not found")

def get_agency_candidate_counts(agency: Agency) -> dict:
    """
    Returns total candidates, shortlisted, interviewing, and rejected counts for the agency.
    """
    counts = Candidate.objects.filter(agency=agency).aggregate(
        total=Count('id'),
        shortlisted=Count('id', filter=Q(status='shortlisted')),
        interviewing=Count('id', filter=Q(status='interviewing')),
        rejected=Count('id', filter=Q(status='rejected'))
    )
    return {
        "total_candidates": counts['total'] or 0,
        "shortlisted": counts['shortlisted'] or 0,
        "interviewing": counts['interviewing'] or 0,
        "rejected": counts['rejected'] or 0
    }

def get_candidate_notes(agency: Agency, candidate_id: int) -> QuerySet[Note]:
    """
    Returns notes associated with the candidate for the agency.
    """
    candidate = get_agency_candidate_by_id(agency, candidate_id)
    return Note.objects.filter(
        agency=agency,
        model='candidate',
        model_id=candidate.id
    ).select_related('user').order_by('-created_at')

def get_candidate_activities(agency: Agency, candidate_id: int) -> QuerySet[Activity]:
    """
    Returns activities associated with the candidate for the agency.
    """
    candidate = get_agency_candidate_by_id(agency, candidate_id)
    return Activity.objects.filter(
        agency=agency,
        model='candidate',
        model_id=candidate.id
    ).select_related('user').order_by('-created_at')

def add_note_to_candidate(agency: Agency, user: User, candidate_id: int, content: str) -> Note:
    """
    Verifies candidate existence and adds a note to it.
    """
    candidate = get_agency_candidate_by_id(agency, candidate_id)
    note = Note.objects.create(
        content=content,
        model='candidate',
        model_id=candidate.id,
        user=user,
        agency=agency
    )
    return note

def get_job_candidates(agency: Agency, job_id: int) -> QuerySet[Candidate]:
    """
    Returns candidates applying for a specific job under the agency.
    """
    from apps.agency.services.jobs import get_agency_job_by_id
    job = get_agency_job_by_id(agency, job_id)
    return Candidate.objects.filter(agency=agency, job=job).prefetch_related('ai_analysis').order_by('-applied_at')


def shortlist_candidate(agency: Agency, candidate_id: int, user=None) -> Candidate:
    """
    If the candidate status is new, make the status shortlisted.
    """
    from rest_framework.exceptions import ValidationError
    candidate = get_agency_candidate_by_id(agency, candidate_id)
    if candidate.status != 'new':
        raise ValidationError("Candidate must have 'new' status to be shortlisted.")
    
    candidate.status = 'shortlisted'
    candidate.save()

    Activity.objects.create(
        model='candidate',
        model_id=candidate.id,
        agency=agency,
        user=user,
        summary=f"Shortlisted candidate {candidate.name} for job {candidate.job.title}"
    )

    return candidate


def schedule_candidate_interview(agency: Agency, recruiter: User, candidate_id: int, meeting_time, duration: int, agenda: str = None) -> tuple[Candidate, 'CandidateMeeting', str | None]:
    """
    Creates a Zoom meeting (or falls back to mock link on error), sends invitation email, and sets status to interviewing.
    """
    from rest_framework.exceptions import ValidationError
    from apps.integrations.models import Integration
    from apps.integrations.services.zoom import create_zoom_meeting
    from apps.agency.models import CandidateMeeting
    from django.core.mail import send_mail
    from django.conf import settings
    import logging

    logger = logging.getLogger(__name__)

    candidate = get_agency_candidate_by_id(agency, candidate_id)
    if candidate.status != 'shortlisted':
        raise ValidationError("Candidate must be shortlisted to schedule an interview.")

    try:
        integration = Integration.objects.select_related('zoom_token').get(
            user=recruiter, agency=agency, provider='zoom', is_connected=True
        )
    except Integration.DoesNotExist:
        raise ValidationError("Zoom is not connected. Please connect your Zoom account first.")

    zoom_token = getattr(integration, 'zoom_token', None)
    if not zoom_token:
        raise ValidationError("Zoom tokens not found. Please reconnect your Zoom account.")

    topic = f"Interview with {candidate.name} for {candidate.job.title}"
    meeting_link = None
    zoom_error_details = None

    from rest_framework.exceptions import APIException
    from rest_framework import status

    class ServiceUnavailable(APIException):
        status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        default_detail = 'Zoom service is temporarily unavailable. Please try again.'
        default_code = 'service_unavailable'

    try:
        meeting_data = create_zoom_meeting(
            zoom_token=zoom_token,
            topic=topic,
            start_time=meeting_time.isoformat(),
            duration=duration,
            agenda=agenda,
        )
        meeting_link = meeting_data.get('join_url')
    except Exception as e:
        logger.error(f"Zoom API meeting creation failed: {e}")
        import requests
        if isinstance(e, requests.HTTPError):
            try:
                zoom_error_details = e.response.json().get('message')
            except Exception:
                zoom_error_details = e.response.text
        else:
            zoom_error_details = str(e)
        raise ServiceUnavailable(detail=f"Zoom API Error: {zoom_error_details}")

    meeting = CandidateMeeting.objects.create(
        candidate=candidate,
        agency=agency,
        user=recruiter,
        meeting_time=meeting_time,
        agenda=agenda,
        summary=f"Interview scheduled via Zoom: {topic}",
        meeting_link=meeting_link,
        status='scheduled'
    )

    # Send email
    email_subject = f"Interview Invitation: {candidate.job.title}"
    email_body = (
        f"Dear {candidate.name},\n\n"
        f"You have been scheduled for an interview for the position of '{candidate.job.title}'.\n\n"
        f"Meeting Details:\n"
        f"- Time: {meeting_time.strftime('%Y-%m-%d %H:%M:%S')} UTC\n"
        f"- Duration: {duration} minutes\n"
        f"- Zoom Link: {meeting_link}\n"
    )
    if agenda:
        email_body += f"- Agenda: {agenda}\n"
    email_body += f"\nBest regards,\n{recruiter.full_name or recruiter.email}\n"

    try:
        send_mail(
            email_subject,
            email_body,
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@teamplayers.com'),
            [candidate.email],
            fail_silently=False
        )
    except Exception as mail_err:
        logger.error(f"Failed to send interview invitation email to {candidate.email}: {mail_err}")

    candidate.status = 'interviewing'
    candidate.save()

    Activity.objects.create(
        model='candidate',
        model_id=candidate.id,
        agency=agency,
        user=recruiter,
        summary=f"Scheduled interview for candidate {candidate.name} on {meeting_time.strftime('%Y-%m-%d %H:%M:%S')} UTC"
    )

    return candidate, meeting, zoom_error_details


def make_candidate_offer(agency: Agency, recruiter: User, candidate_id: int, salary, notice_period: int) -> tuple[Candidate, 'Placement']:
    """
    Transitions candidate to offered, creates Placement.
    """
    from rest_framework.exceptions import ValidationError
    from apps.agency.models import Placement
    from django.core.mail import send_mail
    from django.conf import settings
    import logging

    logger = logging.getLogger(__name__)

    candidate = get_agency_candidate_by_id(agency, candidate_id)
    if candidate.status not in ['shortlisted', 'interviewing']:
        raise ValidationError("Candidate must be shortlisted or interviewing to send an offer.")

    placement = Placement.objects.create(
        candidate=candidate,
        job=candidate.job,
        agency=agency,
        user=recruiter,
        salary=salary,
        notice_period=notice_period,
        status='placed'
    )

    email_subject = f"Job Offer: {candidate.job.title}"
    email_body = (
        f"Dear {candidate.name},\n\n"
        f"We are pleased to extend an offer for the position of '{candidate.job.title}'.\n\n"
        f"Offer Details:\n"
        f"- Salary: {salary}\n"
        f"- Notice Period: {notice_period} days\n\n"
        f"Please let us know your decision.\n\n"
        f"Best regards,\n{recruiter.full_name or recruiter.email}\n"
    )

    try:
        send_mail(
            email_subject,
            email_body,
            getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@teamplayers.com'),
            [candidate.email],
            fail_silently=False
        )
    except Exception as mail_err:
        logger.error(f"Failed to send offer email to {candidate.email}: {mail_err}")

    candidate.status = 'offered'
    candidate.save()

    Activity.objects.create(
        model='candidate',
        model_id=candidate.id,
        agency=agency,
        user=recruiter,
        summary=f"Sent job offer to candidate {candidate.name} with salary {salary}"
    )

    return candidate, placement


def accept_candidate(agency: Agency, candidate_id: int, user=None) -> Candidate:
    """
    Sets candidate status to accepted and updates related placement status to 'placed'.
    """
    candidate = get_agency_candidate_by_id(agency, candidate_id)
    candidate.status = 'accepted'
    candidate.save()

    from apps.agency.models import Placement
    Placement.objects.filter(candidate=candidate).update(status='placed')

    Activity.objects.create(
        model='candidate',
        model_id=candidate.id,
        agency=agency,
        user=user,
        summary=f"Candidate {candidate.name} accepted the job offer"
    )

    return candidate


def reject_candidate(agency: Agency, candidate_id: int, user=None) -> Candidate:
    """
    Sets candidate status to rejected and updates related placement status to 'not_placed'.
    """
    candidate = get_agency_candidate_by_id(agency, candidate_id)
    candidate.status = 'rejected'
    candidate.save()

    from apps.agency.models import Placement
    Placement.objects.filter(candidate=candidate).update(status='not_placed')

    Activity.objects.create(
        model='candidate',
        model_id=candidate.id,
        agency=agency,
        user=user,
        summary=f"Candidate {candidate.name} was rejected / declined the offer"
    )

    return candidate


def save_cv_file(file) -> str:
    """
    Saves an uploaded CV file using Django's default storage system.
    Returns the relative file path.
    """
    from django.core.files.storage import default_storage
    file_path = default_storage.save(f'candidates/resumes/{file.name}', file)
    return file_path


def create_candidate_from_resume(agency: Agency, job, cv_file, user=None) -> Candidate:
    """
    Saves the uploaded CV file, parses it using the AI Candidate Parser,
    creates the Candidate object, scores the candidate against the Job,
    generates an AI explanation, and creates a CandidateAIAnalysis model.
    """
    from django.conf import settings
    from pathlib import Path
    from apps.ai.candidate_import import import_candidate
    from apps.ai.candidate_parser import CandidateParser
    from apps.ai.job_parser import JobParser
    from apps.ai.candidate_scorer import CandidateScorer
    from apps.ai.candidate_explainer import CandidateExplainer
    from apps.agency.models import CandidateAIAnalysis
    from apps.ai.models.candidate import CandidateProfile
    import logging

    logger = logging.getLogger(__name__)

    # 1. Save uploaded file
    file_path = save_cv_file(cv_file)
    absolute_path = Path(settings.MEDIA_ROOT) / file_path
    extension = absolute_path.suffix.lower().lstrip('.')

    # 2. Read resume text using AI readers
    resume_text = ""
    try:
        resume_text = import_candidate(str(absolute_path), extension)
    except Exception as e:
        logger.error(f"Failed to read candidate CV file: {e}")

    # 3. Parse resume details using CandidateParser
    profile = None
    raw_json = None
    if resume_text:
        try:
            parser = CandidateParser()
            profile = parser.parse_candidate(resume_text)
            if profile:
                raw_json = profile.model_dump()
        except Exception as e:
            logger.error(f"Failed to parse candidate profile using LLM: {e}")

    # Fallback to default profile if parsing failed or text was unreadable
    if not profile:
        default_name = Path(cv_file.name).stem.replace('_', ' ').replace('-', ' ').title()
        profile = CandidateProfile(
            full_name=default_name,
            email=None,
            phone=None,
            location=None,
            total_experience_years=0.0,
            technical_skills=[]
        )
        raw_json = profile.model_dump()

    # 4. Create candidate database object
    candidate = Candidate.objects.create(
        agency=agency,
        job=job,
        resume=file_path,
        name=profile.full_name or "Unknown Candidate",
        email=profile.email or "",
        phone=profile.phone or "",
        location=profile.location or "",
        experience=int(profile.total_experience_years) if profile.total_experience_years is not None else 0,
        skills=profile.technical_skills or [],
        current_salary=profile.current_salary or "",
        expected_salary=profile.expected_salary or "",
        ai_extracted_raw_json=raw_json
    )

    # 5. Trigger AI scoring, AI explanation, and create CandidateAIAnalysis
    try:
        # Parse the job description into a JobDescription Pydantic model
        job_parser = JobParser()
        job_desc = job_parser.parse_job_description(job.description)

        # Score the candidate against the Job
        scorer = CandidateScorer()
        score = scorer.score_candidate(profile, job_desc)

        # Generate explanation for the score
        explainer = CandidateExplainer()
        explanation = explainer.generate_explanation(score)

        skills_score = score.skills_match.score if (score and score.skills_match) else 0.0
        exp_score = score.experience_match.score if (score and score.experience_match) else 0.0
        sal_score = score.salary_alignment.score if (score and score.salary_alignment) else 0.0
        loc_score = score.location_alignment.score if (score and score.location_alignment) else 0.0
        overall_match = (skills_score + exp_score + sal_score + loc_score) / 4.0

        concerns = []
        if explanation:
            if explanation.missing_requirements:
                concerns.extend(explanation.missing_requirements)
            if explanation.red_flags:
                concerns.extend(explanation.red_flags)

        CandidateAIAnalysis.objects.create(
            candidate=candidate,
            agency=agency,
            summary=explanation.recruiter_summary if explanation else "AI Analysis generated.",
            key_strength=explanation.key_strengths if explanation else [],
            potential_concerns=concerns,
            skills_match=skills_score,
            experience_match=exp_score,
            salary_match=sal_score,
            location_match=loc_score,
            overall_match_percentage=overall_match
        )
    except Exception as e:
        logger.error(f"Failed to generate candidate AI analysis: {e}")
        # Create a default blank CandidateAIAnalysis on failure so the candidate page still opens
        CandidateAIAnalysis.objects.create(
            candidate=candidate,
            agency=agency,
            summary="AI Analysis could not be generated due to an error.",
            key_strength=[],
            potential_concerns=[],
            skills_match=0.0,
            experience_match=0.0,
            salary_match=0.0,
            location_match=0.0,
            overall_match_percentage=0.0
        )

    Activity.objects.create(
        model='candidate',
        model_id=candidate.id,
        agency=agency,
        user=user,
        summary=f"Uploaded CV and created candidate profile for {candidate.name}"
    )

    return candidate




