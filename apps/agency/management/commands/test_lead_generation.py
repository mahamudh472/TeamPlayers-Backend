import json
from django.core.management.base import BaseCommand
from django.conf import settings
from apps.accounts.models import User
from apps.agency.models import Agency, Leads, LeadGenerationSession
from apps.agency.serializers import LeadWebhookResponseSerializer
from apps.agency.services.lead_generation import (
    create_lead_generation_session,
    trigger_n8n_lead_generation,
    _process_apify_lead_generation_in_background
)

class Command(BaseCommand):
    help = "Test lead generation with static or custom data using either Apify or n8n provider."

    def add_arguments(self, parser):
        parser.add_argument("--provider", type=str, choices=["apify", "n8n"], default=None, help="Provider to use (apify or n8n)")
        parser.add_argument("--country", type=str, default="Germany", help="Target country")
        parser.add_argument("--industry", type=str, default="Automotive", help="Target industry")
        parser.add_argument("--company-size", type=str, default="50-200", help="Target company size")
        parser.add_argument("--hiring-activity", type=str, default="active", help="Target hiring activity")

    def handle(self, *args, **options):
        provider = (options.get("provider") or getattr(settings, "LEAD_GENERATION_PROVIDER", "n8n")).lower()
        country = options.get("country")
        industry = options.get("industry")
        company_size = options.get("company_size")
        hiring_activity = options.get("hiring_activity")

        self.stdout.write(self.style.NOTICE(f"=== Testing Lead Generation (Provider: {provider}) ==="))
        self.stdout.write(f"Parameters: Country='{country}', Industry='{industry}', Size='{company_size}', Activity='{hiring_activity}'")

        # Resolve or create test User and Agency
        user = User.objects.first()
        if not user:
            user = User.objects.create(email="test_recruiter@example.com", full_name="Test Recruiter")

        agency = Agency.objects.first()
        if not agency:
            agency = Agency.objects.create(name="Test Agency", owner=user)

        # 1. Create session
        session = create_lead_generation_session(
            agency=agency,
            user=user,
            country=country,
            industry=industry,
            company_size=company_size,
            hiring_activity=hiring_activity
        )
        self.stdout.write(self.style.SUCCESS(f"Created LeadGenerationSession ID: {session.id}"))

        # 2. Execute based on provider
        if provider == "apify":
            self.stdout.write("Running Apify lead generation in foreground...")
            _process_apify_lead_generation_in_background(
                session_id=str(session.id),
                agency_id=agency.id,
                user_id=str(user.id)
            )
            session.refresh_from_db()
            self.stdout.write(self.style.SUCCESS(f"Session Status: {session.status}"))

            # Query newly generated leads
            recent_leads = Leads.objects.filter(agency=agency).order_by('-created_at')[:10]
            serializer = LeadWebhookResponseSerializer(recent_leads, many=True)
            output = {
                "session_id": str(session.id),
                "status": session.status,
                "leads_count": recent_leads.count(),
                "leads": serializer.data
            }
            self.stdout.write(json.dumps(output, indent=2))

        else:
            self.stdout.write("Triggering n8n lead generation webhook...")
            try:
                trigger_n8n_lead_generation(session)
                session.refresh_from_db()
                self.stdout.write(self.style.SUCCESS(f"Successfully triggered n8n. Session Status: {session.status}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"Failed to trigger n8n: {e}"))
