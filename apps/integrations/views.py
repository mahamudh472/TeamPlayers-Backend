import logging

import requests
from django.conf import settings
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.generics import GenericAPIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response

from apps.agency.models import Agency
from .models import Integration
from .serializers import (
    IntegrationSerializer,
    ZoomMeetingCreateSerializer,
    AvailableIntegrationSerializer,
)
from .services import (
    get_zoom_auth_url,
    exchange_zoom_code,
    store_zoom_tokens,
    create_zoom_meeting,
    disconnect_zoom,
    get_available_integrations,
)

logger = logging.getLogger(__name__)


class IntegrationListView(GenericAPIView):
    """List all integrations for the current user + agency."""

    serializer_class = IntegrationSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agency_id = request.agency_id
        if not agency_id:
            return Response(
                {"error": "X-Agency-ID header is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        integrations = Integration.objects.filter(
            user=request.user, agency_id=agency_id
        )
        serializer = self.get_serializer(integrations, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class AvailableIntegrationListView(GenericAPIView):
    """List all available integrations and connection status for the current user + agency."""

    serializer_class = AvailableIntegrationSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agency_id = request.agency_id
        if not agency_id:
            return Response(
                {"error": "X-Agency-ID header is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = get_available_integrations(request.user, agency_id)
        serializer = self.get_serializer(data, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)



class ZoomConnectView(GenericAPIView):
    """Returns the Zoom OAuth authorization URL with user/agency state."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        agency_id = request.agency_id
        if not agency_id:
            return Response(
                {"error": "X-Agency-ID header is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        state = f"{request.user.id}:{agency_id}"
        auth_url = get_zoom_auth_url(state=state)
        return Response({"auth_url": auth_url}, status=status.HTTP_200_OK)


class ZoomCallbackView(GenericAPIView):
    """
    Zoom OAuth callback endpoint.
    Exchanges the authorization code for tokens and redirects to the frontend.
    """

    permission_classes = [AllowAny]

    def get(self, request):
        code = request.query_params.get('code')
        if not code:
            return redirect(
                f"{settings.FRONTEND_URL}/integrations?status=error&message=missing_code"
            )

        # Retrieve user and agency from session state passed via query params
        user_id = request.query_params.get('state', '')
        if not user_id:
            return redirect(
                f"{settings.FRONTEND_URL}/integrations?status=error&message=missing_state"
            )

        try:
            parts = user_id.split(':')
            if len(parts) != 2:
                raise ValueError("Invalid state format")
            user_id, agency_id = parts[0], parts[1]
        except (ValueError, IndexError):
            return redirect(
                f"{settings.FRONTEND_URL}/integrations?status=error&message=invalid_state"
            )

        try:
            from apps.accounts.models import User
            user = User.objects.get(id=user_id)
            agency = Agency.objects.get(id=agency_id)
        except (User.DoesNotExist, Agency.DoesNotExist):
            return redirect(
                f"{settings.FRONTEND_URL}/integrations?status=error&message=invalid_user_or_agency"
            )

        try:
            token_data = exchange_zoom_code(code)
            store_zoom_tokens(user, agency, token_data)
            return redirect(
                f"{settings.FRONTEND_URL}/integrations?status=success&provider=zoom"
            )
        except requests.RequestException as e:
            logger.error("Zoom OAuth token exchange failed: %s", str(e))
            return redirect(
                f"{settings.FRONTEND_URL}/integrations?status=error&message=token_exchange_failed"
            )


class ZoomDisconnectView(GenericAPIView):
    """Disconnects the user's Zoom integration."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        agency_id = request.agency_id
        if not agency_id:
            return Response(
                {"error": "X-Agency-ID header is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            integration = Integration.objects.get(
                user=request.user, agency_id=agency_id, provider='zoom'
            )
        except Integration.DoesNotExist:
            return Response(
                {"error": "Zoom integration not found"},
                status=status.HTTP_404_NOT_FOUND,
            )

        disconnect_zoom(integration)
        return Response(
            {"message": "Zoom integration disconnected successfully"},
            status=status.HTTP_200_OK,
        )


class ZoomCreateMeetingView(GenericAPIView):
    """Creates a Zoom meeting for the authenticated user."""

    serializer_class = ZoomMeetingCreateSerializer
    permission_classes = [IsAuthenticated]

    def post(self, request):
        agency_id = request.agency_id
        if not agency_id:
            return Response(
                {"error": "X-Agency-ID header is required"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = self.get_serializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        try:
            integration = Integration.objects.select_related('zoom_token').get(
                user=request.user, agency_id=agency_id, provider='zoom', is_connected=True
            )
        except Integration.DoesNotExist:
            return Response(
                {"error": "Zoom is not connected. Please connect your Zoom account first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        zoom_token = getattr(integration, 'zoom_token', None)
        if not zoom_token:
            return Response(
                {"error": "Zoom tokens not found. Please reconnect your Zoom account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            meeting_data = create_zoom_meeting(
                zoom_token=zoom_token,
                topic=serializer.validated_data['topic'],
                start_time=serializer.validated_data['start_time'].isoformat(),
                duration=serializer.validated_data['duration'],
                agenda=serializer.validated_data.get('agenda'),
            )
            return Response(
                {
                    "message": "Meeting created successfully",
                    "meeting": {
                        "id": meeting_data.get('id'),
                        "topic": meeting_data.get('topic'),
                        "start_time": meeting_data.get('start_time'),
                        "duration": meeting_data.get('duration'),
                        "join_url": meeting_data.get('join_url'),
                        "start_url": meeting_data.get('start_url'),
                        "password": meeting_data.get('password', ''),
                    },
                },
                status=status.HTTP_201_CREATED,
            )
        except requests.RequestException as e:
            logger.error("Failed to create Zoom meeting: %s", str(e))
            return Response(
                {"error": "Failed to create meeting on Zoom. Please try again."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
