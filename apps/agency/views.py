from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework import status
from django.conf import settings
from apps.agency.models import Agency
from apps.agency.services import get_user_agencies, get_verified_agency
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
    NoteSerializer
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



