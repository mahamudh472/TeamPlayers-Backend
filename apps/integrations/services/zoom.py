import base64
import logging
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.utils import timezone

from apps.integrations.models import Integration, ZoomToken

logger = logging.getLogger(__name__)

ZOOM_AUTH_URL = 'https://zoom.us/oauth/authorize'
ZOOM_TOKEN_URL = 'https://zoom.us/oauth/token'
ZOOM_API_BASE = 'https://api.zoom.us/v2'
ZOOM_REVOKE_URL = 'https://zoom.us/oauth/revoke'


def _get_basic_auth_header():
    """Build Base64-encoded Basic auth header for Zoom client credentials."""
    credentials = f"{settings.ZOOM_CLIENT_ID}:{settings.ZOOM_CLIENT_SECRET}"
    encoded = base64.b64encode(credentials.encode()).decode()
    return f"Basic {encoded}"


def get_zoom_auth_url(state=''):
    """Build the Zoom OAuth authorization URL the frontend should redirect to."""
    params = {
        'response_type': 'code',
        'client_id': settings.ZOOM_CLIENT_ID,
        'redirect_uri': settings.ZOOM_REDIRECT_URI,
    }
    if state:
        params['state'] = state
    return f"{ZOOM_AUTH_URL}?{urlencode(params)}"


def exchange_zoom_code(code):
    """Exchange an authorization code for access + refresh tokens."""
    response = requests.post(
        ZOOM_TOKEN_URL,
        headers={
            'Authorization': _get_basic_auth_header(),
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        data={
            'grant_type': 'authorization_code',
            'code': code,
            'redirect_uri': settings.ZOOM_REDIRECT_URI,
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def _refresh_zoom_token(zoom_token):
    """Use the refresh token to obtain a new access token from Zoom."""
    response = requests.post(
        ZOOM_TOKEN_URL,
        headers={
            'Authorization': _get_basic_auth_header(),
            'Content-Type': 'application/x-www-form-urlencoded',
        },
        data={
            'grant_type': 'refresh_token',
            'refresh_token': zoom_token.refresh_token,
        },
        timeout=15,
    )
    response.raise_for_status()
    token_data = response.json()

    zoom_token.access_token = token_data['access_token']
    zoom_token.refresh_token = token_data['refresh_token']
    zoom_token.expires_at = timezone.now() + timedelta(seconds=token_data['expires_in'])
    zoom_token.scope = token_data.get('scope', '')
    zoom_token.save()

    return zoom_token


def get_valid_access_token(zoom_token):
    """Return a valid access token, refreshing if expired."""
    buffer = timedelta(minutes=2)
    if timezone.now() >= (zoom_token.expires_at - buffer):
        zoom_token = _refresh_zoom_token(zoom_token)
    return zoom_token.access_token


def _fetch_zoom_user_profile(access_token):
    """Fetch the authenticated Zoom user's profile."""
    response = requests.get(
        f"{ZOOM_API_BASE}/users/me",
        headers={'Authorization': f"Bearer {access_token}"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return {
        'zoom_user_id': data.get('id', ''),
        'email': data.get('email', ''),
        'display_name': data.get('display_name', ''),
        'account_id': data.get('account_id', ''),
    }


def store_zoom_tokens(user, agency, token_data):
    """Create or update Integration + ZoomToken records after OAuth callback."""
    integration, _ = Integration.objects.update_or_create(
        user=user,
        agency=agency,
        provider='zoom',
        defaults={
            'is_connected': True,
            'connected_at': timezone.now(),
        },
    )

    expires_at = timezone.now() + timedelta(seconds=token_data['expires_in'])

    ZoomToken.objects.update_or_create(
        integration=integration,
        defaults={
            'access_token': token_data['access_token'],
            'refresh_token': token_data['refresh_token'],
            'token_type': token_data.get('token_type', 'bearer'),
            'expires_at': expires_at,
            'scope': token_data.get('scope', ''),
        },
    )

    # Fetch Zoom profile and store as metadata
    try:
        profile = _fetch_zoom_user_profile(token_data['access_token'])
        integration.metadata = profile
        integration.save(update_fields=['metadata'])
    except requests.RequestException:
        logger.warning("Failed to fetch Zoom profile for user %s", user.email)

    return integration


def create_zoom_meeting(zoom_token, topic, start_time, duration, agenda=None):
    """Create a Zoom meeting via the Zoom API."""
    access_token = get_valid_access_token(zoom_token)

    payload = {
        'topic': topic,
        'type': 2,  # Scheduled meeting
        'start_time': start_time,
        'duration': duration,
        'timezone': 'UTC',
    }
    if agenda:
        payload['agenda'] = agenda

    response = requests.post(
        f"{ZOOM_API_BASE}/users/me/meetings",
        headers={
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json',
        },
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def disconnect_zoom(integration):
    """Revoke Zoom tokens and mark the integration as disconnected."""
    zoom_token = getattr(integration, 'zoom_token', None)

    if zoom_token:
        try:
            requests.post(
                ZOOM_REVOKE_URL,
                headers={
                    'Authorization': _get_basic_auth_header(),
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                data={'token': zoom_token.access_token},
                timeout=15,
            )
        except requests.RequestException:
            logger.warning("Failed to revoke Zoom token for integration %s", integration.id)
        zoom_token.delete()

    integration.is_connected = False
    integration.connected_at = None
    integration.metadata = {}
    integration.save(update_fields=['is_connected', 'connected_at', 'metadata'])
