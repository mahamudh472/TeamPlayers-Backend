import json
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.accounts.models import User
from apps.agency.models import Agency, Job, Candidate, CandidateGatheringSession
from apps.agency.serializers import CandidateDetailSerializer
from apps.agency.services.candidate_gathering import (
    create_candidate_gathering_session,
    trigger_n8n_candidate_gathering,
    _process_apify_candidate_gathering_in_background
)

class Command(BaseCommand):
    help = "Test candidate gathering with static or custom data using either Apify or n8n provider."

    def add_arguments(self, parser):
        parser.add_argument("--provider", type=str, choices=["apify", "n8n"], default=None, help="Provider to use (apify or n8n)")
        parser.add_argument("--job-id", type=int, default=None, help="Existing Job ID to gather candidates for")
        parser.add_argument("--job-title", type=str, default="Senior Python Django Developer", help="Job title if creating sample job")
        parser.add_argument("--skills", type=str, default="Python, Django, PostgreSQL, REST API", help="Comma-separated skills")
        parser.add_argument("--location", type=str, default="Berlin, Germany", help="Job location")

    def handle(self, *args, **options):
        provider = (options.get("provider") or getattr(settings, "CANDIDATE_GATHERING_PROVIDER", "n8n")).lower()
        job_id = options.get("job_id")
        job_title = options.get("job_title")
        skills_raw = options.get("skills")
        location = options.get("location")

        skills = [s.strip() for s in skills_raw.split(",") if s.strip()]

        self.stdout.write(self.style.NOTICE(f"=== Testing Candidate Gathering (Provider: {provider}) ==="))

        # Resolve or create test User and Agency
        user = User.objects.first()
        if not user:
            user = User.objects.create(email="test_recruiter@example.com", full_name="Test Recruiter")

        agency = Agency.objects.first()
        if not agency:
            agency = Agency.objects.create(name="Test Agency", owner=user)

        # Resolve or create test Job
        job = None
        if job_id:
            try:
                job = Job.objects.get(id=job_id, agency=agency)
            except Job.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Job with ID {job_id} not found."))
                return

        if not job:
            job = Job.objects.filter(agency=agency).first()
            if not job:
                job = Job.objects.create(
                    agency=agency,
                    title=job_title,
                    description=f"Looking for an experienced {job_title} with strong skills in {', '.join(skills)}.",
                    location=location,
                    experince_required=4,
                    skills=skills,
                    job_type="Full-Time"
                )

        self.stdout.write(f"Using Job ID: {job.id} ('{job.title}'), Location: '{job.location}', Skills: {job.skills}")

        # 1. Create session
        session = create_candidate_gathering_session(
            agency=agency,
            job=job,
            user=user
        )
        self.stdout.write(self.style.SUCCESS(f"Created CandidateGatheringSession ID: {session.id}"))

        # 2. Execute based on provider
        if provider == "apify":
            self.stdout.write("Running Apify candidate gathering in foreground...")
            _process_apify_candidate_gathering_in_background(
                session_id=str(session.id),
                agency_id=agency.id,
                job_id=job.id,
                user_id=str(user.id)
            )
            session.refresh_from_db()
            self.stdout.write(self.style.SUCCESS(f"Session Status: {session.status}"))

            # Query gathered candidates for this job
            candidates = Candidate.objects.filter(job=job).order_by('-applied_at')[:10]
            serializer = CandidateDetailSerializer(candidates, many=True)
            output = {
                "session_id": str(session.id),
                "job_id": job.id,
                "status": session.status,
                "candidates_count": candidates.count(),
                "candidates": serializer.data
            }
            self.stdout.write(json.dumps(output, indent=2, default=str))

        else:
            self.stdout.write("Triggering n8n candidate gathering webhook...")
            try:
                trigger_n8n_candidate_gathering(session)
                session.refresh_from_db()
                self.stdout.write(self.style.SUCCESS(f"Successfully triggered n8n. Session Status: {session.status}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to trigger n8n: {e}"))
