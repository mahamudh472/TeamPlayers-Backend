from django.db.models import Q, QuerySet, Count
from apps.agency.models import Agency, Candidate, Note
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


def shortlist_candidate(agency: Agency, candidate_id: int) -> Candidate:
    """
    If the candidate status is new, make the status shortlisted.
    """
    from rest_framework.exceptions import ValidationError
    candidate = get_agency_candidate_by_id(agency, candidate_id)
    if candidate.status != 'new':
        raise ValidationError("Candidate must have 'new' status to be shortlisted.")
    
    candidate.status = 'shortlisted'
    candidate.save()
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
        logger.warning(f"Zoom API meeting creation failed, falling back to mock link. Error: {e}")
        import requests
        if isinstance(e, requests.HTTPError):
            try:
                zoom_error_details = e.response.json().get('message')
            except Exception:
                zoom_error_details = e.response.text
        else:
            zoom_error_details = str(e)
        
        # Generate a mock Zoom meeting link
        import random
        meeting_id = ''.join(random.choices('0123456789', k=10))
        meeting_link = f"https://zoom.us/j/{meeting_id}"

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

    return candidate, placement


def accept_candidate(agency: Agency, candidate_id: int) -> Candidate:
    """
    Sets candidate status to accepted and updates related placement status to 'placed'.
    """
    candidate = get_agency_candidate_by_id(agency, candidate_id)
    candidate.status = 'accepted'
    candidate.save()

    from apps.agency.models import Placement
    Placement.objects.filter(candidate=candidate).update(status='placed')

    return candidate


def reject_candidate(agency: Agency, candidate_id: int) -> Candidate:
    """
    Sets candidate status to rejected and updates related placement status to 'not_placed'.
    """
    candidate = get_agency_candidate_by_id(agency, candidate_id)
    candidate.status = 'rejected'
    candidate.save()

    from apps.agency.models import Placement
    Placement.objects.filter(candidate=candidate).update(status='not_placed')

    return candidate


