from django.db.models import Q, QuerySet
from apps.agency.models import Agency, Client, Job, Activity
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

def calculate_job_weights_with_ai(job_data: dict) -> dict:
    """
    Uses AI to evaluate job requirements and calculate priority weights
    for the 5 candidate scoring dimensions (skills, experience, salary, location, certification).
    """
    import logging
    logger = logging.getLogger(__name__)

    default_weights = {
        'skills_weight': 20.0,
        'experience_weight': 20.0,
        'salary_weight': 20.0,
        'location_weight': 20.0,
        'certification_weight': 20.0,
    }

    try:
        from apps.ai.job_weights_analyzer import JobWeightsAnalyzer
        analyzer = JobWeightsAnalyzer()
        result = analyzer.evaluate_weights(
            job_title=job_data.get('title', ''),
            description=job_data.get('description', ''),
            skills=job_data.get('skills', []),
            location=job_data.get('location', ''),
            experience_required=job_data.get('experince_required', 0),
            job_type=job_data.get('job_type', ''),
            salary_range=job_data.get('salary_range', '')
        )
        if result:
            w_s = max(0.0, float(result.skills_weight))
            w_e = max(0.0, float(result.experience_weight))
            w_sa = max(0.0, float(result.salary_weight))
            w_l = max(0.0, float(result.location_weight))
            w_c = max(0.0, float(result.certification_weight))
            total = w_s + w_e + w_sa + w_l + w_c
            if total > 0 and round(total, 2) != 100.0:
                w_s = round((w_s / total) * 100.0, 2)
                w_e = round((w_e / total) * 100.0, 2)
                w_sa = round((w_sa / total) * 100.0, 2)
                w_l = round((w_l / total) * 100.0, 2)
                w_c = round(100.0 - (w_s + w_e + w_sa + w_l), 2)
            return {
                'skills_weight': w_s,
                'experience_weight': w_e,
                'salary_weight': w_sa,
                'location_weight': w_l,
                'certification_weight': w_c,
            }
    except Exception as e:
        logger.warning(f"Failed to calculate job weights using AI: {e}. Falling back to default weights.")

    return default_weights


def recalculate_job_candidates_score(job: Job) -> int:
    """
    Recalculates overall_match_percentage for all candidate analyses associated with this job
    using the job's updated scoring priority weights.
    """
    from apps.agency.models import CandidateAIAnalysis

    w_skills = job.skills_weight if job.skills_weight is not None else 20.0
    w_exp = job.experience_weight if job.experience_weight is not None else 20.0
    w_sal = job.salary_weight if job.salary_weight is not None else 20.0
    w_loc = job.location_weight if job.location_weight is not None else 20.0
    w_cert = job.certification_weight if job.certification_weight is not None else 20.0
    total_weight = w_skills + w_exp + w_sal + w_loc + w_cert

    analyses = CandidateAIAnalysis.objects.filter(candidate__job=job)
    updated_count = 0
    for analysis in analyses:
        if total_weight > 0:
            score = (
                (analysis.skills_match * w_skills) +
                (analysis.experience_match * w_exp) +
                (analysis.salary_match * w_sal) +
                (analysis.location_match * w_loc) +
                (analysis.certification_match * w_cert)
            ) / total_weight
        else:
            score = (
                analysis.skills_match +
                analysis.experience_match +
                analysis.salary_match +
                analysis.location_match +
                analysis.certification_match
            ) / 5.0
        analysis.overall_match_percentage = round(score, 2)
        analysis.save(update_fields=['overall_match_percentage', 'updated_at'])
        updated_count += 1
    return updated_count


def create_agency_job(agency: Agency, job_data: dict, user=None) -> Job:
    """
    Creates a new job for the given agency.
    If priority weights are not explicitly provided, triggers AI to calculate them based on the job description.
    """
    weight_keys = ['skills_weight', 'experience_weight', 'salary_weight', 'location_weight', 'certification_weight']
    has_custom_weights = all(job_data.get(k) is not None for k in weight_keys)

    if has_custom_weights:
        weights = {k: float(job_data[k]) for k in weight_keys}
    else:
        ai_weights = calculate_job_weights_with_ai(job_data)
        weights = {
            k: float(job_data.get(k)) if job_data.get(k) is not None else ai_weights.get(k, 20.0)
            for k in weight_keys
        }

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
        description_file=job_data.get('description_file'),
        skills_weight=weights['skills_weight'],
        experience_weight=weights['experience_weight'],
        salary_weight=weights['salary_weight'],
        location_weight=weights['location_weight'],
        certification_weight=weights['certification_weight']
    )

    Activity.objects.create(
        model='job',
        model_id=job.id,
        agency=agency,
        user=user,
        summary=f"Created job {job.title}"
    )

    return job

def update_agency_job(agency: Agency, job: Job, job_data: dict, user=None) -> Job:
    """
    Updates a job manually with the given data.
    If priority weights are updated, recalculates candidate overall match scores for this job.
    """
    weight_keys = {'skills_weight', 'experience_weight', 'salary_weight', 'location_weight', 'certification_weight'}
    weights_modified = False

    for field, value in job_data.items():
        if field in weight_keys and getattr(job, field) != value:
            weights_modified = True
        setattr(job, field, value)
    job.save()

    if weights_modified:
        recalculate_job_candidates_score(job)

    Activity.objects.create(
        model='job',
        model_id=job.id,
        agency=agency,
        user=user,
        summary=f"Updated job details for {job.title}"
    )

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
    total_applicants = Candidate.objects.filter(agency=agency, is_processing=False).count()
    shortlisted = Candidate.objects.filter(agency=agency, status='shortlisted', is_processing=False).count()
    interviewed = Candidate.objects.filter(agency=agency, status='interviewing', is_processing=False).count()

    return {
        "active_jobs": active_jobs,
        "total_applicants": total_applicants,
        "shortlisted": shortlisted,
        "interviewed": interviewed
    }

def get_job_applicants_count(job: Job) -> int:
    return job.candidates.filter(is_processing=False).count()

def get_job_shortlisted_count(job: Job) -> int:
    return job.candidates.filter(status='shortlisted', is_processing=False).count()

def get_job_interviewed_count(job: Job) -> int:
    return job.candidates.filter(status='interviewing', is_processing=False).count()





