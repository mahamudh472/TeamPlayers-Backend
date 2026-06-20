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

