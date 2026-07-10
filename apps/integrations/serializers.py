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

