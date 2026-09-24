from rest_framework import serializers
from .models import Integration


class IntegrationSerializer(serializers.ModelSerializer):
    """Read-only serializer for listing connected integrations."""

    class Meta:
        model = Integration
        fields = [
            'id', 'provider', 'is_connected', 'connected_at', 'metadata',
            'created_at', 'updated_at',
        ]
        read_only_fields = fields


class ZoomMeetingCreateSerializer(serializers.Serializer):
    """Validates input for creating a Zoom meeting."""

    topic = serializers.CharField(max_length=200)
    start_time = serializers.DateTimeField(
        help_text="Meeting start time in ISO 8601 format (e.g. 2025-07-20T10:00:00Z)"
    )
    duration = serializers.IntegerField(
        min_value=1, max_value=1440,
        help_text="Meeting duration in minutes"
    )
    agenda = serializers.CharField(max_length=2000, required=False, allow_blank=True)


class AvailableIntegrationSerializer(serializers.Serializer):
    """Serializer for available integrations status."""
    id = serializers.UUIDField(allow_null=True)
    provider = serializers.CharField()
    name = serializers.CharField()
    is_connected = serializers.BooleanField()
    connected_at = serializers.DateTimeField(allow_null=True)
    metadata = serializers.JSONField()
    created_at = serializers.DateTimeField(allow_null=True)
    updated_at = serializers.DateTimeField(allow_null=True)


class MicrosoftSendMailSerializer(serializers.Serializer):
    """Validates input for sending an email via Microsoft Graph API."""

    recipient_email = serializers.EmailField()
    subject = serializers.CharField(max_length=255)
    body = serializers.CharField()
    content_type = serializers.ChoiceField(
        choices=['Text', 'HTML'], default='Text', required=False
    )


class MicrosoftCreateEventSerializer(serializers.Serializer):
    """Validates input for creating a calendar event via Microsoft Graph API."""

    subject = serializers.CharField(max_length=255)
    start_time = serializers.DateTimeField(
        help_text="Event start time in ISO 8601 format (e.g. 2026-09-25T10:00:00Z)"
    )
    end_time = serializers.DateTimeField(
        required=False, allow_null=True,
        help_text="Event end time in ISO 8601 format. If omitted, duration is used."
    )
    duration = serializers.IntegerField(
        min_value=1, max_value=1440, required=False, default=60,
        help_text="Event duration in minutes (used if end_time is omitted)"
    )
    body = serializers.CharField(
        max_length=2000, required=False, allow_blank=True, default=''
    )
    location = serializers.CharField(
        max_length=255, required=False, allow_blank=True, default=''
    )


