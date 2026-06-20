import uuid
from django.db import models
from apps.accounts.models import User
from apps.agency.models import Agency


class Integration(models.Model):
    """Tracks third-party service connections per user per agency."""

    PROVIDER_CHOICES = [
        ('zoom', 'Zoom'),
        ('outlook', 'Outlook'),
        ('google_calendar', 'Google Calendar'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='integrations')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='integrations')
    provider = models.CharField(max_length=30, choices=PROVIDER_CHOICES)
    is_connected = models.BooleanField(default=False)
    connected_at = models.DateTimeField(blank=True, null=True)
    metadata = models.JSONField(default=dict, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'integrations'
        unique_together = ('user', 'agency', 'provider')
        verbose_name = 'Integration'
        verbose_name_plural = 'Integrations'

    def __str__(self):
        return f"{self.user.email} - {self.provider} ({self.agency.name})"


class ZoomToken(models.Model):
    """Stores Zoom OAuth tokens linked to an Integration record."""

    integration = models.OneToOneField(
        Integration, on_delete=models.CASCADE, related_name='zoom_token'
    )
    access_token = models.TextField()
    refresh_token = models.TextField()
    token_type = models.CharField(max_length=20, default='bearer')
    expires_at = models.DateTimeField()
    scope = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'zoom_tokens'
        verbose_name = 'Zoom Token'
        verbose_name_plural = 'Zoom Tokens'

    def __str__(self):
        return f"ZoomToken for {self.integration}"
