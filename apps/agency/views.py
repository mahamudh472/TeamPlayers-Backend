from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from apps.agency.models import Agency
from django.utils import timezone
from apps.agency.services import (
    get_user_agencies,
    get_verified_agency,
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
    add_note_to_candidate,
    get_job_candidates,
    shortlist_candidate,
    schedule_candidate_interview,
    make_candidate_offer,
    accept_candidate,
    reject_candidate,
    get_public_active_jobs,
    get_public_active_job_by_id,
    save_cv_file,
    get_agency_placements,
    get_agency_placement_counts
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
    UserAgencySerializer,
    LeadSerializer,
    LeadDetailSerializer,
    NoteSerializer,
    ClientSerializer,
    ClientDetailSerializer,
    JobSerializer,
    ClientActivitySerializer,
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
    CalendarMeetingSerializer
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
            
        lead = update_lead_status(agency, pk, status_val)
        serializer = LeadSerializer(lead)
        return Response(serializer.data, status=status.HTTP_200_OK)


class ClientListView(APIView):
    """
    API endpoint to list and search clients, or create a client manually.
    
    GET:
        Returns a paginated list of clients for the agency.
        Supports search via '?search=<query>' across company, contact details, location, and industry.
        Includes static summary statistics: active_clients, total_revenue, placement_rate.
        
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
        # TODO: Replace static values with dynamic calculations once data tracking is implemented.
        active_clients = agency.clients.count()
        total_revenue_sum = agency.revenues.aggregate(total=Sum('amount'))['total']
        total_revenue = float(total_revenue_sum) if total_revenue_sum is not None else 0.0
        placement_rate = 85.5

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
        
        updated_client = update_client(agency, client, serializer.validated_data)
        return Response({"message": "Client updated successfully"}, status=status.HTTP_200_OK)


class JobListView(APIView):
    """
    API endpoint to list and search jobs, or create a job.

    GET:
        Returns a paginated list of jobs for the agency.
        Supports search via '?search=<query>' across title, description, location, and client company.
        Includes static summary statistics: active_jobs, total_applicants, shortlisted, avg_time_to_fill.

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

        # Static values for summary fields
        active_jobs = 8
        total_applicants = 42
        shortlisted = 15
        avg_time_to_fill = 18.5

        paginator = self.pagination_class()
        page = paginator.paginate_queryset(jobs, request, view=self)
        if page is not None:
            serializer = JobSerializer(page, many=True, context={'agency': agency})
            return Response({
                "count": paginator.page.paginator.count,
                "next": paginator.get_next_link(),
                "previous": paginator.get_previous_link(),
                "active_jobs": active_jobs,
                "total_applicants": total_applicants,
                "shortlisted": shortlisted,
                "avg_time_to_fill": avg_time_to_fill,
                "results": serializer.data
            }, status=status.HTTP_200_OK)

        serializer = JobSerializer(jobs, many=True, context={'agency': agency})
        return Response({
            "active_jobs": active_jobs,
            "total_applicants": total_applicants,
            "shortlisted": shortlisted,
            "avg_time_to_fill": avg_time_to_fill,
            "results": serializer.data
        }, status=status.HTTP_200_OK)

    def post(self, request):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        serializer = JobSerializer(data=request.data, context={'agency': agency})
        serializer.is_valid(raise_exception=True)

        job = create_agency_job(agency, serializer.validated_data)
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

        updated_job = update_agency_job(agency, job, serializer.validated_data)
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
        
        candidate = shortlist_candidate(agency, pk)
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

        candidate = accept_candidate(agency, pk)
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

        candidate = reject_candidate(agency, pk)
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
    Returns saved file path and URL.
    """
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CVUploadSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        cv_file = serializer.validated_data['file']
        file_path = save_cv_file(cv_file)

        # Build absolute URL using request
        file_url = request.build_absolute_uri(settings.MEDIA_URL + file_path)

        return Response({
            "message": "CV uploaded successfully",
            "file_path": file_path,
            "file_url": file_url
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






