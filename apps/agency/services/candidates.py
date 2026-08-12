from django.db.models import Q, QuerySet, Count, Subquery, OuterRef, F
from apps.agency.models import Agency, Candidate, Note, Activity, CandidateAIAnalysis, CandidateProfile
from apps.accounts.models import User
from rest_framework.exceptions import NotFound

def get_agency_candidates(agency: Agency, search_query: str = None) -> QuerySet[Candidate]:
    """
    Returns candidates for the agency, optionally filtered by a search query.
    Performs case-insensitive checks on name, email, location, and job title.
    Ordered by latest AI analysis overall match percentage descending, fallback to applied_at.
    """
    latest_analysis = CandidateAIAnalysis.objects.filter(
        candidate=OuterRef('pk')
    ).order_by('-created_at')

    queryset = (
        Candidate.objects.filter(agency=agency, is_processing=False)
        .annotate(match_score=Subquery(latest_analysis.values('overall_match_percentage')[:1]))
        .select_related('job')
        .prefetch_related('ai_analysis')
        .order_by(F('match_score').desc(nulls_last=True), '-applied_at')
    )
    if search_query:
        queryset = queryset.filter(
            Q(profile__name__icontains=search_query) |
            Q(profile__email__icontains=search_query) |
            Q(profile__location__icontains=search_query) |
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
    counts = Candidate.objects.filter(agency=agency, is_processing=False).aggregate(
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
    Ordered by latest AI analysis overall match percentage descending, fallback to applied_at.
    """
    from apps.agency.services.jobs import get_agency_job_by_id
    job = get_agency_job_by_id(agency, job_id)
    
    latest_analysis = CandidateAIAnalysis.objects.filter(
        candidate=OuterRef('pk')
    ).order_by('-created_at')

    return (
        Candidate.objects.filter(agency=agency, job=job, is_processing=False)
        .annotate(match_score=Subquery(latest_analysis.values('overall_match_percentage')[:1]))
        .prefetch_related('ai_analysis')
        .order_by(F('match_score').desc(nulls_last=True), '-applied_at')
    )


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


def process_candidate_ai_match(candidate, profile, job, agency) -> 'CandidateAIAnalysis':
    """
    Triggers AI scoring, AI explanation, and creates a CandidateAIAnalysis record.
    """
    from apps.ai.job_parser import JobParser
    from apps.ai.candidate_scorer import CandidateScorer
    from apps.ai.candidate_explainer import CandidateExplainer
    from apps.agency.models import CandidateAIAnalysis
    import logging

    logger = logging.getLogger(__name__)

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

        return CandidateAIAnalysis.objects.create(
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
        return CandidateAIAnalysis.objects.create(
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


def _process_resume_in_background(candidate_id, absolute_path, extension, cv_filename, agency_id, job_id, user_id=None):
    from apps.agency.models import Candidate, Agency, Job, Activity, CandidateAIAnalysis, CandidateProfile
    from apps.accounts.models import User
    from django.conf import settings
    from pathlib import Path
    from apps.ai.candidate_import import import_candidate
    from apps.ai.candidate_parser import CandidateParser
    from apps.ai.models.candidate import CandidateProfile as AICandidateProfile
    from django.db import close_old_connections
    import logging

    logger = logging.getLogger(__name__)

    try:
        candidate = Candidate.objects.get(id=candidate_id)
        agency = Agency.objects.get(id=agency_id)
        job = Job.objects.get(id=job_id)
        user = User.objects.get(id=user_id) if user_id else None

        # 1. Read resume text using AI readers
        resume_text = ""
        try:
            resume_text = import_candidate(str(absolute_path), extension)
        except Exception as e:
            logger.error(f"Failed to read candidate CV file: {e}")

        # 2. Parse resume details using CandidateParser
        profile_data = None
        raw_json = None
        if resume_text:
            try:
                parser = CandidateParser()
                profile_data = parser.parse_candidate(resume_text)
                if profile_data:
                    raw_json = profile_data.model_dump()
            except Exception as e:
                logger.error(f"Failed to parse candidate profile using LLM: {e}")

        # Fallback to default profile_data if parsing failed or text was unreadable
        if not profile_data:
            default_name = Path(cv_filename).stem.replace('_', ' ').replace('-', ' ').title()
            profile_data = AICandidateProfile(
                full_name=default_name,
                email=None,
                phone=None,
                location=None,
                total_experience_years=0.0,
                technical_skills=[]
            )
            raw_json = profile_data.model_dump()

        # Update or merge CandidateProfile
        email = profile_data.email or ""
        phone = profile_data.phone or ""

        db_profile = None
        if email:
            db_profile = CandidateProfile.objects.filter(agency=agency, email=email).exclude(id=candidate.profile.id).first()
        if not db_profile and phone:
            db_profile = CandidateProfile.objects.filter(agency=agency, phone=phone).exclude(id=candidate.profile.id).first()

        temp_profile = candidate.profile

        if db_profile:
            # We found an existing profile. Associate the candidate application with it, and delete the temporary one
            candidate.profile = db_profile
            candidate.save()
            if temp_profile:
                temp_profile.delete()
        else:
            # No existing profile, we use and update the temporary one
            db_profile = temp_profile

        # Update db_profile fields with parsed details
        db_profile.name = profile_data.full_name or db_profile.name
        db_profile.email = profile_data.email or db_profile.email
        db_profile.phone = profile_data.phone or db_profile.phone or ""
        db_profile.location = profile_data.location or db_profile.location or ""
        db_profile.experience = int(profile_data.total_experience_years) if profile_data.total_experience_years is not None else 0
        db_profile.skills = profile_data.technical_skills or []
        db_profile.current_salary = profile_data.current_salary or ""
        db_profile.expected_salary = profile_data.expected_salary or ""
        db_profile.ai_extracted_raw_json = raw_json
        db_profile.save()

        # Check for existing candidate application and handle versioning
        candidate = handle_candidate_versioning(agency, job, db_profile, candidate)

        # 4. Trigger AI scoring, AI explanation, and create CandidateAIAnalysis
        process_candidate_ai_match(candidate, profile_data, job, agency)

        candidate.is_processing = False
        candidate.save()


        # Send notifications to all active, accepted agency members
        from apps.agency.models import AgencyMember
        from apps.notifications.services.notifications import create_notification
        try:
            members = AgencyMember.objects.filter(agency=agency, is_active=True, invitation_status='accepted').select_related('user')
            for member in members:
                create_notification(
                    user=member.user,
                    title="Candidate Processing Complete",
                    message=f"Candidate {candidate.name} has been processed successfully for job {job.title}.",
                    notification_type="candidate_processed",
                    source={"candidate_id": candidate.id, "job_id": job.id}
                )
        except Exception as notification_err:
            logger.error(f"Failed to send resume processing completion notifications: {notification_err}")

        Activity.objects.create(
            model='candidate',
            model_id=candidate.id,
            agency=agency,
            user=user,
            summary=f"Uploaded CV and created candidate profile for {candidate.name}"
        )

    except Exception as outer_err:
        logger.error(f"Error in background resume processing task: {outer_err}")
    finally:
        close_old_connections()


def create_candidate_from_resume(agency: Agency, job, cv_file, user=None) -> Candidate:
    """
    Saves the uploaded CV file, creates a shell Candidate object,
    starts a background thread to parse the CV and generate match score,
    and returns the Candidate object immediately.
    """
    from django.conf import settings
    from pathlib import Path
    import threading
    import logging
    import uuid
    from apps.agency.models import CandidateProfile

    logger = logging.getLogger(__name__)

    # 1. Save uploaded file
    file_path = save_cv_file(cv_file)
    absolute_path = Path(settings.MEDIA_ROOT) / file_path
    extension = absolute_path.suffix.lower().lstrip('.')

    # 2. Derive default candidate name from the file name
    default_name = Path(cv_file.name).stem.replace('_', ' ').replace('-', ' ').title()

    # Create temporary email/phone profile
    temp_email = f"no-email-{uuid.uuid4().hex[:10]}@temp.com"
    profile = CandidateProfile.objects.create(
        agency=agency,
        name=default_name,
        email=temp_email,
        resume=file_path
    )

    # 3. Create candidate shell database object
    candidate = Candidate.objects.create(
        agency=agency,
        job=job,
        profile=profile,
        status='new',
        is_processing=True
    )

    # 4. Start background thread to process the CV
    user_id = user.id if user else None
    thread = threading.Thread(
        target=_process_resume_in_background,
        args=(candidate.id, absolute_path, extension, cv_file.name, agency.id, job.id, user_id)
    )
    thread.daemon = True
    thread.start()

    return candidate


def handle_candidate_versioning(agency, job, db_profile, current_shell_candidate) -> Candidate:
    """
    Checks if a candidate application with matching profile already exists for this job in the agency.
    If it exists, archives its current state to CandidateVersion, updates its profile,
    deletes current_shell_candidate, and returns the existing candidate.
    Otherwise, links current_shell_candidate to profile and returns it.
    """
    from apps.agency.models import CandidateVersion, Candidate

    # Link profile to shell candidate first (so it's associated)
    current_shell_candidate.profile = db_profile
    current_shell_candidate.save()

    # Look for an existing Candidate application for the SAME job and SAME profile in this agency
    existing_candidate = Candidate.objects.filter(
        agency=agency,
        job=job,
        profile=db_profile
    ).exclude(id=current_shell_candidate.id).first()

    if existing_candidate:
        # Create a new version of the existing candidate application before resetting it
        CandidateVersion.objects.create(
            candidate=existing_candidate,
            job=existing_candidate.job,
            name=existing_candidate.profile.name,
            email=existing_candidate.profile.email,
            phone=existing_candidate.profile.phone,
            location=existing_candidate.profile.location,
            experience=existing_candidate.profile.experience,
            skills=existing_candidate.profile.skills,
            current_salary=existing_candidate.profile.current_salary,
            expected_salary=existing_candidate.profile.expected_salary,
            resume=existing_candidate.profile.resume,
            status=existing_candidate.status,
            ai_extracted_raw_json=existing_candidate.profile.ai_extracted_raw_json
        )

        # Copy resume path from the shell candidate to existing candidate's profile if applicable
        if current_shell_candidate.profile.resume:
            existing_candidate.profile.resume = current_shell_candidate.profile.resume
            existing_candidate.profile.save()

        # Reset status for the new application
        existing_candidate.status = 'new'
        existing_candidate.save()

        # Delete the temporary shell candidate
        current_shell_candidate.delete()
        return existing_candidate

    return current_shell_candidate


def _process_multiple_candidates_in_background(text, agency_id, job_id, user_id=None):
    from apps.agency.models import Candidate, Agency, Job, Activity, CandidateProfile
    from apps.accounts.models import User
    from apps.ai.candidate_parser import CandidateParser
    from django.db import close_old_connections
    import logging
    import uuid

    logger = logging.getLogger(__name__)

    try:
        agency = Agency.objects.get(id=agency_id)
        job = Job.objects.get(id=job_id)
        user = User.objects.get(id=user_id) if user_id else None

        # 1. Parse text using CandidateParser
        parser = CandidateParser()
        profiles = []
        try:
            profiles = parser.parse_multiple_candidates(text)
        except Exception as e:
            logger.error(f"Failed to parse multiple candidates from text: {e}")

        # 2. For each parsed candidate profile, create candidate and run match
        for profile_data in profiles:
            try:
                # Find or create CandidateProfile by email/phone
                email = profile_data.email or ""
                phone = profile_data.phone or ""

                db_profile = None
                if email:
                    db_profile = CandidateProfile.objects.filter(agency=agency, email=email).first()
                if not db_profile and phone:
                    db_profile = CandidateProfile.objects.filter(agency=agency, phone=phone).first()

                if not db_profile:
                    db_profile = CandidateProfile.objects.create(
                        agency=agency,
                        name=profile_data.full_name or "Parsed Candidate",
                        email=email or f"no-email-{uuid.uuid4().hex[:10]}@temp.com",
                        phone=phone or ""
                    )

                # Update profile details
                db_profile.name = profile_data.full_name or db_profile.name
                db_profile.email = profile_data.email or db_profile.email
                db_profile.phone = profile_data.phone or db_profile.phone or ""
                db_profile.location = profile_data.location or db_profile.location or ""
                db_profile.experience = int(profile_data.total_experience_years) if profile_data.total_experience_years is not None else 0
                db_profile.skills = profile_data.technical_skills or []
                db_profile.current_salary = profile_data.current_salary or ""
                db_profile.expected_salary = profile_data.expected_salary or ""
                db_profile.ai_extracted_raw_json = profile_data.model_dump()
                db_profile.save()

                # Create shell candidate application (linked to profile)
                candidate = Candidate.objects.create(
                    agency=agency,
                    job=job,
                    profile=db_profile,
                    status='new',
                    is_processing=True
                )

                # Check for existing candidate application and handle versioning
                candidate = handle_candidate_versioning(agency, job, db_profile, candidate)

                # Trigger AI scoring, AI explanation, and create CandidateAIAnalysis
                process_candidate_ai_match(candidate, profile_data, job, agency)

                candidate.is_processing = False
                candidate.save()

                # Send notifications to all active, accepted agency members
                from apps.agency.models import AgencyMember
                from apps.notifications.services.notifications import create_notification
                try:
                    members = AgencyMember.objects.filter(agency=agency, is_active=True, invitation_status='accepted').select_related('user')
                    for member in members:
                        create_notification(
                            user=member.user,
                            title="Candidate Processing Complete",
                            message=f"Candidate {candidate.profile.name} has been processed successfully from text import for job {job.title}.",
                            notification_type="candidate_processed",
                            source={"candidate_id": candidate.id, "job_id": job.id}
                        )
                except Exception as notification_err:
                    logger.error(f"Failed to send resume processing completion notifications: {notification_err}")

                Activity.objects.create(
                    model='candidate',
                    model_id=candidate.id,
                    agency=agency,
                    user=user,
                    summary=f"Imported candidate {candidate.profile.name} from text import"
                )
            except Exception as candidate_err:
                logger.error(f"Error processing individual candidate profile {profile_data.full_name if profile_data else 'unknown'}: {candidate_err}")

    except Exception as outer_err:
        logger.error(f"Error in background multiple candidate processing task: {outer_err}")
    finally:
        close_old_connections()


def create_candidates_from_text(agency: Agency, job, text: str, user=None):
    """
    Starts a background thread to parse multiple candidates from raw text,
    create candidate records, and run AI match analyses.
    """
    import threading
    user_id = user.id if user else None
    thread = threading.Thread(
        target=_process_multiple_candidates_in_background,
        args=(text, agency.id, job.id, user_id)
    )
    thread.daemon = True
    thread.start()








