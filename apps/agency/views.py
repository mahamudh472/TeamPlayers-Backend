from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from apps.agency.models import Agency, Job
from django.utils import timezone
from apps.agency.services import (
    get_user_agencies,
    get_verified_agency,
    update_agency_info,
    get_agency_clients,
    get_agency_client_by_id,
    create_manual_client,
    update_client,
    get_agency_jobs,
    get_agency_job_by_id,
    create_agency_job,
    update_agency_job,
    get_agency_candidates,
    get_agency_candidate_by_id,
    get_agency_candidate_counts,
    get_candidate_notes,
    get_candidate_activities,
    add_note_to_candidate,
    get_job_candidates,
    shortlist_candidate,
    schedule_candidate_interview,
    make_candidate_offer,
    accept_candidate,
    reject_candidate,
    get_public_active_jobs,
    get_public_active_job_by_id,
    get_agency_placements,
    get_agency_placement_counts,
    get_dashboard_data,
    get_analytics_data,
    create_lead_generation_session,
    trigger_n8n_lead_generation
)
from apps.agency.services.leads import (
    get_agency_leads,
    get_agency_lead_by_id,
    get_agency_lead_status_counts,
    add_note_to_lead,
    ingest_bulk_leads,
    update_lead_status
)
from apps.agency.serializers import (
    AgencySerializer,
    UserAgencySerializer,
    LeadSerializer,
    LeadDetailSerializer,
    NoteSerializer,
    ClientSerializer,
    ClientDetailSerializer,
    JobSerializer,
    ClientActivitySerializer,
    CandidateActivitySerializer,
    CandidateMinSerializer,
    CandidateDetailSerializer,
    JobCandidateSerializer,
    CandidateMeetingCreateSerializer,
    CandidateOfferSerializer,
    PlacementSerializer,
    PlacementListSerializer,
    CandidateMeetingSerializer,
    PublicJobSerializer,
    PublicJobDetailSerializer,
    CVUploadSerializer,
    InterviewListSerializer,
    CalendarMeetingSerializer,
    LeadGenerationSerializer,
    LeadGenerationSessionSerializer
)
from apps.agency.services.jobs import get_client_jobs
from apps.agency.services.clients import (
    get_client_activities,
    get_client_notes,
    add_note_to_client
)
from apps.agency.services.meetings import (
    get_agency_meetings,
    get_agency_meeting_counts,
    get_agency_meetings_by_month
)
from apps.agency.paginations import StandardResultsSetPagination

class UserAgencyListView(APIView):
    """
    API endpoint to list agencies and roles for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agencies = get_user_agencies(request.user)
        serializer = UserAgencySerializer(agencies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeadListView(APIView):
    """
    API endpoint to list leads for an agency, with optional status filtering.
    Includes count of leads per status and pagination support.
    Requires header: X-Agency-ID
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        status_filter = request.query_params.get('status')
        leads = get_agency_leads(agency, status_filter)
        status_counts = get_agency_lead_status_counts(agency)
        
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(leads, request, view=self)
        if page is not None:
            serializer = LeadSerializer(page, many=True)
            return Response({
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "status_counts": status_counts,
                "results": serializer.data
            }, status=status.HTTP_200_OK)
            
        serializer = LeadSerializer(leads, many=True)
        return Response({
            "leads": serializer.data,
            "status_counts": status_counts
        }, status=status.HTTP_200_OK)



class LeadDetailView(APIView):
    """
    API endpoint to retrieve details of a single lead, including its notes.
    Requires header: X-Agency-ID
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        lead = get_agency_lead_by_id(agency, pk)
        serializer = LeadDetailSerializer(lead)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeadAddNoteView(APIView):
    """
    API endpoint to add a note to a lead.
    Requires header: X-Agency-ID
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        content = request.data.get('content')
        if not content or not content.strip():
            return Response(
                {"error": "content is required and cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        note = add_note_to_lead(agency, request.user, pk, content)
        serializer = NoteSerializer(note)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LeadWebhookIngestView(APIView):
    """
    API endpoint (webhook) for external services to inject leads in JSON format.
    Requires agency_id and the global webhook secret in the payload.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        agency_id = request.data.get('agency_id')
        secret = request.data.get('secret')
        leads_data = request.data.get('leads')

        # 1. Validate the secret
        expected_secret = getattr(settings, 'LEADS_WEBHOOK_SECRET', 'default_leads_webhook_secret_key')
        if not secret or secret != expected_secret:
            return Response(
                {"detail": "Invalid or missing webhook secret"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # 2. Validate agency_id
        if not agency_id:
            return Response(
                {"detail": "agency_id is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            agency = Agency.objects.get(id=agency_id)
        except (Agency.DoesNotExist, ValueError):
            return Response(
                {"detail": "Agency not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3. Validate leads
        if not leads_data or not isinstance(leads_data, list):
            return Response(
                {"detail": "leads must be a non-empty list"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate each lead using the LeadSerializer
        serializer = LeadSerializer(data=leads_data, many=True)
        if not serializer.is_valid():
            return Response(
                {"detail": "Validation failed for one or more leads", "errors": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 4. Ingest bulk leads
        created_leads = ingest_bulk_leads(agency, serializer.validated_data)
        response_serializer = LeadSerializer(created_leads, many=True)
        return Response({
            "message": f"Successfully created {len(created_leads)} leads",
            "created_leads": response_serializer.data
        }, status=status.HTTP_201_CREATED)


class LeadChangeStatusView(APIView):
    """
    API endpoint to change the status of a lead.
    Requires header: X-Agency-ID
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        status_val = request.data.get('status')
        if not status_val:
            return Response(
                {"error": "status is required"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        lead = update_lead_status(agency, pk, status_val, user=request.user)
        serializer = LeadSerializer(lead)
        return Response(serializer.data, status=status.HTTP_200_OK)


class LeadGenerationView(APIView):
    """
    API endpoint to trigger AI lead generation.
    Creates a LeadGenerationSession object and sends a request to n8n webhook.
    Requires header: X-Agency-ID
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        serializer = LeadGenerationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        session = create_lead_generation_session(
            agency=agency,
            user=request.user,
            **serializer.validated_data
        )

        trigger_n8n_lead_generation(session)

        response_serializer = LeadGenerationSessionSerializer(session)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class ClientListView(APIView):
    """
    API endpoint to list and search clients, or create a client manually.
    
    GET:
        Returns a paginated list of clients for the agency.
        Supports search via '?search=<query>' across company, contact details, location, and industry.
        Includes dynamic summary statistics: active_clients, total_revenue, placement_rate.
        
    POST:
        Manually creates a new client for the agency.
        Requires client details in payload.
        
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        search_query = request.query_params.get('search')
        clients = get_agency_clients(agency, search_query)
        
        from django.db.models import Sum
        from apps.agency.services import get_agency_placement_rate
        active_clients = agency.clients.count()
        total_revenue_sum = agency.revenues.aggregate(total=Sum('amount'))['total']
        total_revenue = float(total_revenue_sum) if total_revenue_sum is not None else 0.0
        placement_rate = get_agency_placement_rate(agency)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(clients, request, view=self)
        if page is not None:
            serializer = ClientSerializer(page, many=True)
            return Response({
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "active_clients": active_clients,
                "total_revenue": total_revenue,
                "placement_rate": placement_rate,
                "results": serializer.data
            }, status=status.HTTP_200_OK)
            
        serializer = ClientSerializer(clients, many=True)
        return Response({
            "active_clients": active_clients,
            "total_revenue": total_revenue,
            "placement_rate": placement_rate,
            "results": serializer.data
        }, status=status.HTTP_200_OK)


    def post(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        serializer = ClientSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        client = create_manual_client(agency, serializer.validated_data, user=request.user)
        return Response({"message": "Client created successfully"}, status=status.HTTP_201_CREATED)


class ClientDetailView(APIView):
    """
    API endpoint to retrieve or update details of a specific client.
    
    GET:
        Returns client profile details by ID.
        
    PATCH:
        Partially updates client profile details.
        
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        client = get_agency_client_by_id(agency, pk)
        serializer = ClientDetailSerializer(client)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        client = get_agency_client_by_id(agency, pk)
        serializer = ClientDetailSerializer(client, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        
        updated_client = update_client(agency, client, serializer.validated_data, user=request.user)
        return Response({"message": "Client updated successfully"}, status=status.HTTP_200_OK)


class JobListView(APIView):
    """
    API endpoint to list and search jobs, or create a job.

    GET:
        Returns a paginated list of jobs for the agency.
        Supports search via '?search=<query>' across title, description, location, and client company.
        Includes dynamic summary statistics: active_jobs, total_applicants, shortlisted, and interviewed.

    POST:
        Creates a new job for the agency.
        Requires job details in payload.

    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        search_query = request.query_params.get('search')
        jobs = get_agency_jobs(agency, search_query)

        from apps.agency.services import get_agency_job_stats
        stats = get_agency_job_stats(agency)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(jobs, request, view=self)
        if page is not None:
            serializer = JobSerializer(page, many=True, context={'agency': agency})
            return Response({
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "active_jobs": stats["active_jobs"],
                "total_applicants": stats["total_applicants"],
                "shortlisted": stats["shortlisted"],
                "interviewed": stats["interviewed"],
                "results": serializer.data
            }, status=status.HTTP_200_OK)

        serializer = JobSerializer(jobs, many=True, context={'agency': agency})
        return Response({
            "active_jobs": stats["active_jobs"],
            "total_applicants": stats["total_applicants"],
            "shortlisted": stats["shortlisted"],
            "interviewed": stats["interviewed"],
            "results": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        serializer = JobSerializer(data=request.data, context={'agency': agency})
        serializer.is_valid(raise_exception=True)

        job = create_agency_job(agency, serializer.validated_data, user=request.user)
        response_serializer = JobSerializer(job)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class JobDetailView(APIView):
    """
    API endpoint to retrieve or update details of a specific job.

    GET:
        Returns job details by ID.

    PATCH:
        Partially updates job details.

    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        job = get_agency_job_by_id(agency, pk)
        serializer = JobSerializer(job, context={'agency': agency})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        job = get_agency_job_by_id(agency, pk)
        serializer = JobSerializer(job, data=request.data, partial=True, context={'agency': agency})
        serializer.is_valid(raise_exception=True)

        updated_job = update_agency_job(agency, job, serializer.validated_data, user=request.user)
        response_serializer = JobSerializer(updated_job)
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class ClientJobsListView(APIView):
    """
    API endpoint to list jobs for a specific client.
    By default, it filters to active (open) jobs, matching the 'Active Jobs' UI section.
    Requires header: X-Agency-ID
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        # Default to 'open' status for active jobs section, support overriding
        status_filter = request.query_params.get('status', 'open')
        if status_filter == 'all':
            status_filter = None

        jobs = get_client_jobs(agency, pk, status_filter=status_filter)
        serializer = JobSerializer(jobs, many=True, context={'agency': agency})
        return Response(serializer.data, status=status.HTTP_200_OK)


class ClientActivityListView(APIView):
    """
    API endpoint to list activities for a specific client.
    Requires header: X-Agency-ID
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        activities = get_client_activities(agency, pk)
        serializer = ClientActivitySerializer(activities, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CandidateActivityListView(APIView):
    """
    API endpoint to list activities for a specific candidate.
    Requires header: X-Agency-ID
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        activities = get_candidate_activities(agency, pk)
        serializer = CandidateActivitySerializer(activities, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ClientNotesView(APIView):
    """
    API endpoint to list and add notes for a specific client.
    Requires header: X-Agency-ID
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        notes = get_client_notes(agency, pk)
        serializer = NoteSerializer(notes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        content = request.data.get('content')
        if not content or not content.strip():
            return Response(
                {"error": "content is required and cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST
            )

        note = add_note_to_client(agency, request.user, pk, content)
        serializer = NoteSerializer(note)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CandidateListView(APIView):
    """
    API endpoint to list and search candidates.
    GET:
        Returns a paginated list of candidates for the agency.
        Supports search via '?search=<query>'.
        Includes status counts: total_candidates, shortlisted, interviewing, rejected.
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        search_query = request.query_params.get('search')
        candidates = get_agency_candidates(agency, search_query)
        counts = get_agency_candidate_counts(agency)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(candidates, request, view=self)
        if page is not None:
            serializer = CandidateMinSerializer(page, many=True)
            response_data = {
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data
            }
            response_data.update(counts)
            return Response(response_data, status=status.HTTP_200_OK)

        serializer = CandidateMinSerializer(candidates, many=True)
        response_data = {
            "results": serializer.data
        }
        response_data.update(counts)
        return Response(response_data, status=status.HTTP_200_OK)

    def post(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        serializer = CVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job_id = serializer.validated_data['job']
        try:
            job = Job.objects.get(id=job_id, agency=agency)
        except (Job.DoesNotExist, ValueError):
            return Response(
                {"job": "Job not found or does not belong to this agency."},
                status=status.HTTP_404_NOT_FOUND
            )

        cv_file = serializer.validated_data['file']

        from apps.agency.services.candidates import create_candidate_from_resume
        candidate = create_candidate_from_resume(agency, job, cv_file, user=request.user)

        response_serializer = CandidateDetailSerializer(candidate, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class CandidateDetailView(APIView):
    """
    API endpoint to retrieve details of a specific candidate.
    GET:
        Returns candidate details including AI analysis, job info, and recommended actions.
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        candidate = get_agency_candidate_by_id(agency, pk)
        serializer = CandidateDetailSerializer(candidate, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CandidateNotesView(APIView):
    """
    API endpoint to list and add notes for a specific candidate.
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        notes = get_candidate_notes(agency, pk)
        serializer = NoteSerializer(notes, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        content = request.data.get('content')
        if not content or not content.strip():
            return Response(
                {"error": "content is required and cannot be empty"},
                status=status.HTTP_400_BAD_REQUEST
            )

        note = add_note_to_candidate(agency, request.user, pk, content)
        serializer = NoteSerializer(note)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class JobCandidatesListView(APIView):
    """
    API endpoint to list candidates of a specific job.
    GET:
        Returns a list of candidates applying for the job.
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        candidates = get_job_candidates(agency, pk)
        serializer = JobCandidateSerializer(candidates, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class CandidateShortlistView(APIView):
    """
    API endpoint to shortlist a candidate (new -> shortlisted).
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        candidate = shortlist_candidate(agency, pk, user=request.user)
        serializer = CandidateDetailSerializer(candidate, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CandidateInterviewMeetingView(APIView):
    """
    API endpoint to schedule an interview meeting for a shortlisted candidate.
    Creates a Zoom meeting, sends invitation email, and sets status to interviewing.
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        serializer = CandidateMeetingCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        candidate, meeting, zoom_error_details = schedule_candidate_interview(
            agency=agency,
            recruiter=request.user,
            candidate_id=pk,
            meeting_time=serializer.validated_data['meeting_time'],
            duration=serializer.validated_data['duration'],
            agenda=serializer.validated_data.get('agenda')
        )

        candidate_data = CandidateDetailSerializer(candidate, context={'request': request}).data
        meeting_data = CandidateMeetingSerializer(meeting).data

        response_data = {
            "message": "Interview meeting scheduled and invitation email sent successfully.",
            "candidate": candidate_data,
            "meeting": meeting_data
        }

        if zoom_error_details:
            response_data["zoom_warning"] = f"Zoom meeting creation failed: {zoom_error_details}. A mock Zoom link was generated instead."

        return Response(response_data, status=status.HTTP_201_CREATED)


class CandidateOfferSendView(APIView):
    """
    API endpoint to send a job offer to a shortlisted/interviewing candidate.
    Transitions status to offered and creates a Placement object.
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        serializer = CandidateOfferSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        candidate, placement = make_candidate_offer(
            agency=agency,
            recruiter=request.user,
            candidate_id=pk,
            salary=serializer.validated_data['salary'],
            notice_period=serializer.validated_data['notice_period']
        )

        candidate_data = CandidateDetailSerializer(candidate, context={'request': request}).data
        placement_data = PlacementSerializer(placement).data

        return Response({
            "message": "Offer sent and placement created successfully.",
            "candidate": candidate_data,
            "placement": placement_data
        }, status=status.HTTP_201_CREATED)


class CandidateAcceptView(APIView):
    """
    API endpoint to set candidate status to accepted from any status.
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        candidate = accept_candidate(agency, pk, user=request.user)
        serializer = CandidateDetailSerializer(candidate, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CandidateRejectView(APIView):
    """
    API endpoint to set candidate status to rejected from any status.
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        candidate = reject_candidate(agency, pk, user=request.user)
        serializer = CandidateDetailSerializer(candidate, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicJobListView(APIView):
    """
    API endpoint to list and search active (open) jobs publicly across all agencies.
    """
    permission_classes = [AllowAny]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        search_query = request.query_params.get('search')
        jobs = get_public_active_jobs(search_query)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(jobs, request, view=self)
        if page is not None:
            serializer = PublicJobSerializer(page, many=True, context={'request': request})
            return paginator.get_paginated_response(serializer.data)

        serializer = PublicJobSerializer(jobs, many=True, context={'request': request})
        return Response({
            "results": serializer.data
        }, status=status.HTTP_200_OK)


class PublicJobDetailView(APIView):
    """
    API endpoint to retrieve public details of a specific job.
    """
    permission_classes = [AllowAny]

    def get(self, request, pk):
        job = get_public_active_job_by_id(pk)
        serializer = PublicJobDetailSerializer(job, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class PublicCVUploadView(APIView):
    """
    API endpoint for public users to upload a CV/resume.
    Parses the resume details and creates candidate and AI analysis records.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        job_id = serializer.validated_data['job']
        try:
            job = Job.objects.get(id=job_id)
        except (Job.DoesNotExist, ValueError):
            return Response(
                {"job": "Job not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        agency = job.agency
        cv_file = serializer.validated_data['file']

        from apps.agency.services.candidates import create_candidate_from_resume
        candidate = create_candidate_from_resume(agency, job, cv_file)

        # Build absolute URL using request
        file_url = request.build_absolute_uri(settings.MEDIA_URL + str(candidate.resume))
        candidate_data = CandidateDetailSerializer(candidate, context={'request': request}).data

        return Response({
            "message": "CV uploaded and candidate profile parsed successfully.",
            "file_path": str(candidate.resume),
            "file_url": file_url,
            "candidate": candidate_data
        }, status=status.HTTP_201_CREATED)


class InterviewListView(APIView):
    """
    API endpoint to list and search interview meetings (candidate meetings) for the agency.

    GET:
        Returns a paginated list of interviews.
        Supports status filtering via '?status=<upcoming|completed|scheduled|pending|cancelled|all>'.
        Supports search via '?search=<query>' across candidate name, job title, and client company.
        Includes summary counts: scheduled_count, completed_count, this_week_count.

    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        status_filter = request.query_params.get('status')
        search_query = request.query_params.get('search')

        meetings = get_agency_meetings(agency, status_filter=status_filter, search_query=search_query)
        counts = get_agency_meeting_counts(agency)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(meetings, request, view=self)
        if page is not None:
            serializer = InterviewListSerializer(page, many=True)
            response_data = {
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data
            }
            response_data.update(counts)
            return Response(response_data, status=status.HTTP_200_OK)

        serializer = InterviewListSerializer(meetings, many=True)
        response_data = {
            "results": serializer.data
        }
        response_data.update(counts)
        return Response(response_data, status=status.HTTP_200_OK)


class InterviewCalendarView(APIView):
    """
    API endpoint to list interview meetings for a specific month and year.

    GET:
        Returns a list of meetings with only date/time, candidate name, and position.
        Query params: ?year=<int>&month=<int> (defaults to current year/month).

    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        year_param = request.query_params.get('year')
        month_param = request.query_params.get('month')

        try:
            year = int(year_param) if year_param else timezone.now().year
            month = int(month_param) if month_param else timezone.now().month
            if not (1 <= month <= 12):
                raise ValueError
        except ValueError:
            return Response(
                {"error": "Invalid year or month query parameter"},
                status=status.HTTP_400_BAD_REQUEST
            )

        meetings = get_agency_meetings_by_month(agency, year=year, month=month)
        serializer = CalendarMeetingSerializer(meetings, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PlacementListView(APIView):
    """
    API endpoint to list, search, and filter placements for an agency.

    GET:
        Returns a paginated list of placements.
        Supports status filtering via '?status=<all|offers|active>'.
        Supports search via '?search=<query>' across candidate name, candidate email, job title, and client company.
        Includes tab summary counts: all_count, offers_count, active_count.

    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        status_filter = request.query_params.get('status')
        search_query = request.query_params.get('search')

        placements = get_agency_placements(agency, status_filter=status_filter, search_query=search_query)
        counts = get_agency_placement_counts(agency)

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(placements, request, view=self)
        if page is not None:
            serializer = PlacementListSerializer(page, many=True)
            response_data = {
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "results": serializer.data
            }
            response_data.update(counts)
            return Response(response_data, status=status.HTTP_200_OK)

        serializer = PlacementListSerializer(placements, many=True)
        response_data = {
            "results": serializer.data
        }
        response_data.update(counts)
        return Response(response_data, status=status.HTTP_200_OK)


class DashboardView(APIView):
    """
    API endpoint to retrieve all dashboard statistics, metrics, and trends for the agency.
    Requires header: X-Agency-ID
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        data = get_dashboard_data(agency)
        return Response(data, status=status.HTTP_200_OK)


class AnalyticsView(APIView):
    """
    API endpoint to retrieve detailed analytics, performance insights, and trends for the agency.
    Supports range parameter (e.g. ?range=last_year, last_month, last_3_months, all_time).
    Requires header: X-Agency-ID
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        range_param = request.query_params.get('range', 'last_year')
        data = get_analytics_data(agency, range_param)
        return Response(data, status=status.HTTP_200_OK)


class AgencyInfoView(APIView):
    """
    API endpoint to retrieve and update the details of the active agency.
    GET:
        Returns details of the active agency (id, name, logo).
    PATCH:
        Partially updates agency details (name, logo).
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        serializer = AgencySerializer(agency, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)

    def patch(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        serializer = AgencySerializer(agency, data=request.data, partial=True, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        updated_agency = update_agency_info(agency, serializer.validated_data, user=request.user)
        response_serializer = AgencySerializer(updated_agency, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_200_OK)


class AgencyMemberListView(APIView):
    """
    API endpoint to list and invite agency members.
    GET:
        Returns a list of active agency members (both accepted and pending).
    POST:
        Invites a new member to the agency.
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        from apps.agency.services.members import get_agency_members
        from apps.agency.serializers import AgencyMemberSerializer
        
        members = get_agency_members(agency)
        serializer = AgencyMemberSerializer(members, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def post(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        from apps.agency.serializers import InviteMemberSerializer, AgencyMemberSerializer
        from apps.agency.services.members import invite_agency_member
        
        serializer = InviteMemberSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        member = invite_agency_member(
            agency=agency,
            current_user=request.user,
            email=serializer.validated_data['email'],
            role=serializer.validated_data['role'],
            request=request
        )
        response_serializer = AgencyMemberSerializer(member)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class AgencyMemberDetailView(APIView):
    """
    API endpoint to update or remove an agency member.
    PATCH:
        Updates an agency member's role.
    DELETE:
        Removes an agency member.
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def patch(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        role = request.data.get('role')
        if not role:
            return Response({"role": "This field is required."}, status=status.HTTP_400_BAD_REQUEST)
        if role not in ['owner', 'admin', 'recruiter']:
            return Response({"role": f"'{role}' is not a valid choice."}, status=status.HTTP_400_BAD_REQUEST)
            
        from apps.agency.services.members import update_agency_member_role
        from apps.agency.serializers import AgencyMemberSerializer
        
        member = update_agency_member_role(
            agency=agency,
            current_user=request.user,
            member_id=pk,
            new_role=role
        )
        response_serializer = AgencyMemberSerializer(member)
        return Response(response_serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, pk):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)
        
        from apps.agency.services.members import remove_agency_member
        
        remove_agency_member(
            agency=agency,
            current_user=request.user,
            member_id=pk
        )
        return Response({"message": "Member removed successfully"}, status=status.HTTP_200_OK)


class AcceptInvitationView(APIView):
    """
    Public API endpoint to accept an agency invitation.
    GET:
        Accepts the invitation via the signed token and redirects to the frontend login page.
    """
    permission_classes = [AllowAny]

    def get(self, request):
        token = request.query_params.get('token')
        if not token:
            return Response({"error": "Token query parameter is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        from apps.agency.services.members import accept_agency_invitation
        from django.shortcuts import redirect
        
        accept_agency_invitation(token)
        
        # Redirect to the frontend login page with a success message query param
        redirect_url = f"{settings.FRONTEND_URL}/login?invite_accepted=true"
        return redirect(redirect_url)


class GenerateJobDescriptionView(APIView):
    """
    API endpoint to generate a structured job description using AI.

    POST:
        Accepts a document file (PDF, DOCX, TXT) and/or freeform text.
        Returns a structured job description on success,
        or an error if the input is unrelated or unprocessable.

    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        agency_id = request.agency_id
        get_verified_agency(request.user, agency_id)

        document = request.FILES.get('document')
        text = request.data.get('text')

        from apps.agency.services.job_description import (
            generate_job_description,
        )

        result = generate_job_description(
            document=document,
            text=text,
        )

        if result.get("success"):
            return Response(result, status=status.HTTP_200_OK)

        return Response(
            {
                "error": result.get(
                    "error_message",
                    "Could not generate a job description "
                    "from the provided input.",
                )
            },
            status=status.HTTP_422_UNPROCESSABLE_ENTITY,
        )




