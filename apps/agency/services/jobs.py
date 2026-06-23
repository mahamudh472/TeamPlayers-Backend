from django.db.models import Q, QuerySet
from apps.agency.models import Agency, Client, Job
from rest_framework.exceptions import NotFound

def get_agency_jobs(agency: Agency, search_query: str = None) -> QuerySet[Job]:
    """
    Returns jobs for the agency, optionally filtered by a search query.
    """
    queryset = Job.objects.filter(agency=agency).order_by('-created_at')
    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(client__company__icontains=search_query)
        )
    return queryset

def get_agency_job_by_id(agency: Agency, job_id: int) -> Job:
    """
    Returns a single job for the agency, or raises NotFound.
    """
    try:
        return Job.objects.get(agency=agency, id=job_id)
    except (Job.DoesNotExist, ValueError):
        raise NotFound("Job not found")

def create_agency_job(agency: Agency, job_data: dict) -> Job:
    """
    Creates a new job for the given agency.
    """
    job = Job.objects.create(
        agency=agency,
        client=job_data.get('client'),
        title=job_data.get('title'),
        description=job_data.get('description'),
        location=job_data.get('location'),
        salary_range=job_data.get('salary_range'),
        experince_required=job_data.get('experince_required', 0),
        skills=job_data.get('skills', []),
        job_type=job_data.get('job_type', 'full-time'),
        status=job_data.get('status', 'open'),
        description_file=job_data.get('description_file')
    )
    return job

def update_agency_job(agency: Agency, job: Job, job_data: dict) -> Job:
    """
    Updates a job manually with the given data.
    """
    for field, value in job_data.items():
        setattr(job, field, value)
    job.save()
    return job

def get_client_jobs(agency: Agency, client_id: int, status_filter: str = None) -> QuerySet[Job]:
    """
    Returns jobs associated with a client, optionally filtered by status.
    """
    from apps.agency.services.clients import get_agency_client_by_id
    client = get_agency_client_by_id(agency, client_id)
    queryset = Job.objects.filter(agency=agency, client=client).order_by('-created_at')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    return queryset


def get_public_active_jobs(search_query: str = None) -> QuerySet[Job]:
    """
    Returns only active (open) jobs across all agencies, optionally filtered by a search query.
    Only returns jobs meant for public consumption.
    """
    queryset = Job.objects.filter(status='open').order_by('-created_at')
    if search_query:
        queryset = queryset.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(location__icontains=search_query)
        )
    return queryset


def get_public_active_job_by_id(job_id: int) -> Job:
    """
    Returns an active (open) job, or raises NotFound.
    """
    try:
        return Job.objects.get(id=job_id, status='open')
    except (Job.DoesNotExist, ValueError):
        raise NotFound("Job not found")

def get_agency_job_stats(agency: Agency) -> dict:
    """
    Calculates dynamic summary metrics for an agency's job dashboard.
    """
    from apps.agency.models import Candidate
    active_jobs = Job.objects.filter(agency=agency, status='open').count()
    total_applicants = Candidate.objects.filter(agency=agency).count()
    shortlisted = Candidate.objects.filter(agency=agency, status='shortlisted').count()
    interviewed = Candidate.objects.filter(agency=agency, status='interviewing').count()

    return {
        "active_jobs": active_jobs,
        "total_applicants": total_applicants,
        "shortlisted": shortlisted,
        "interviewed": interviewed
    }

def get_job_applicants_count(job: Job) -> int:
    return job.candidates.count()

def get_job_shortlisted_count(job: Job) -> int:
    return job.candidates.filter(status='shortlisted').count()

def get_job_interviewed_count(job: Job) -> int:
    return job.candidates.filter(status='interviewing').count()



