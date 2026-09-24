import logging
from datetime import timedelta
from urllib.parse import urlencode

import requests
from django.conf import settings
from django.utils import timezone

from apps.integrations.models import Integration, MicrosoftToken

logger = logging.getLogger(__name__)

GRAPH_API_BASE = 'https://graph.microsoft.com/v1.0'


MICROSOFT_AUTH_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/authorize'
MICROSOFT_TOKEN_URL = 'https://login.microsoftonline.com/common/oauth2/v2.0/token'


def get_microsoft_auth_url(state: str = '') -> str:
    """Build the Microsoft OAuth authorization URL for user consent."""
    params = {
        'client_id': settings.MICROSOFT_CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': settings.MICROSOFT_REDIRECT_URI,
        'response_mode': 'query',
        'scope': settings.MICROSOFT_SCOPES,
        'prompt': 'consent',
    }
    if state:
        params['state'] = state
    return f"{MICROSOFT_AUTH_URL}?{urlencode(params)}"


def exchange_microsoft_code(code: str) -> dict:
    """Exchange an authorization code for Microsoft access + refresh tokens."""
    data = {
        'client_id': settings.MICROSOFT_CLIENT_ID,
        'client_secret': settings.MICROSOFT_CLIENT_SECRET,
        'grant_type': 'authorization_code',
        'code': code,
        'redirect_uri': settings.MICROSOFT_REDIRECT_URI,
        'scope': settings.MICROSOFT_SCOPES,
    }
    response = requests.post(
        MICROSOFT_TOKEN_URL,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data=data,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()


def _refresh_microsoft_token(microsoft_token: MicrosoftToken) -> MicrosoftToken:
    """Use the refresh token to obtain a new access token from Microsoft."""
    data = {
        'client_id': settings.MICROSOFT_CLIENT_ID,
        'client_secret': settings.MICROSOFT_CLIENT_SECRET,
        'grant_type': 'refresh_token',
        'refresh_token': microsoft_token.refresh_token,
        'scope': settings.MICROSOFT_SCOPES,
    }
    response = requests.post(
        MICROSOFT_TOKEN_URL,
        headers={'Content-Type': 'application/x-www-form-urlencoded'},
        data=data,
        timeout=15,
    )
    response.raise_for_status()
    token_data = response.json()

    microsoft_token.access_token = token_data['access_token']
    if 'refresh_token' in token_data:
        microsoft_token.refresh_token = token_data['refresh_token']
    microsoft_token.expires_at = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))
    microsoft_token.scope = token_data.get('scope', microsoft_token.scope)
    microsoft_token.save()

    return microsoft_token


def get_valid_microsoft_access_token(microsoft_token: MicrosoftToken) -> str:
    """Return a valid Microsoft access token, refreshing if expired or expiring soon."""
    buffer = timedelta(minutes=2)
    if timezone.now() >= (microsoft_token.expires_at - buffer):
        microsoft_token = _refresh_microsoft_token(microsoft_token)
    return microsoft_token.access_token


def _fetch_microsoft_user_profile(access_token: str) -> dict:
    """Fetch the authenticated user profile from Microsoft Graph API."""
    response = requests.get(
        f"{GRAPH_API_BASE}/me",
        headers={'Authorization': f"Bearer {access_token}"},
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return {
        'microsoft_user_id': data.get('id', ''),
        'display_name': data.get('displayName', ''),
        'email': data.get('mail') or data.get('userPrincipalName', ''),
        'user_principal_name': data.get('userPrincipalName', ''),
        'given_name': data.get('givenName', ''),
        'surname': data.get('surname', ''),
        'job_title': data.get('jobTitle', ''),
    }


def store_microsoft_tokens(user, agency, token_data: dict) -> Integration:
    """Create or update Integration + MicrosoftToken records after OAuth callback."""
    integration, _ = Integration.objects.update_or_create(
        user=user,
        agency=agency,
        provider='microsoft',
        defaults={
            'is_connected': True,
            'connected_at': timezone.now(),
        },
    )

    expires_at = timezone.now() + timedelta(seconds=token_data.get('expires_in', 3600))

    MicrosoftToken.objects.update_or_create(
        integration=integration,
        defaults={
            'access_token': token_data['access_token'],
            'refresh_token': token_data.get('refresh_token', ''),
            'token_type': token_data.get('token_type', 'Bearer'),
            'expires_at': expires_at,
            'scope': token_data.get('scope', ''),
        },
    )

    # Fetch Microsoft user profile and store as metadata
    try:
        profile = _fetch_microsoft_user_profile(token_data['access_token'])
        integration.metadata = profile
        integration.save(update_fields=['metadata'])
    except requests.RequestException:
        logger.warning("Failed to fetch Microsoft profile for user %s", user.email)

    return integration


def disconnect_microsoft(integration: Integration) -> None:
    """Remove Microsoft tokens and mark the integration as disconnected."""
    microsoft_token = getattr(integration, 'microsoft_token', None)
    if microsoft_token:
        microsoft_token.delete()

    integration.is_connected = False
    integration.connected_at = None
    integration.metadata = {}
    integration.save(update_fields=['is_connected', 'connected_at', 'metadata'])


def send_microsoft_email(
    microsoft_token: MicrosoftToken,
    recipient_email: str,
    subject: str,
    body: str,
    content_type: str = 'Text',
) -> None:
    """Send an email on behalf of the user via Microsoft Graph API."""
    access_token = get_valid_microsoft_access_token(microsoft_token)

    payload = {
        'message': {
            'subject': subject,
            'body': {
                'contentType': content_type,
                'content': body,
            },
            'toRecipients': [
                {
                    'emailAddress': {
                        'address': recipient_email,
                    }
                }
            ],
        },
        'saveToSentItems': True,
    }

    response = requests.post(
        f"{GRAPH_API_BASE}/me/sendMail",
        headers={
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json',
        },
        json=payload,
        timeout=15,
    )
    response.raise_for_status()


def create_microsoft_event(
    microsoft_token: MicrosoftToken,
    subject: str,
    start_time,
    end_time=None,
    duration: int = 60,
    body: str = '',
    location: str = '',
) -> dict:
    """Create a calendar event via Microsoft Graph API."""
    access_token = get_valid_microsoft_access_token(microsoft_token)

    if end_time is None:
        if isinstance(start_time, str):
            from dateutil.parser import parse
            start_dt = parse(start_time)
            end_dt = start_dt + timedelta(minutes=duration)
            end_time = end_dt.isoformat()
        else:
            end_time = start_time + timedelta(minutes=duration)

    start_str = start_time.isoformat() if hasattr(start_time, 'isoformat') else str(start_time)
    end_str = end_time.isoformat() if hasattr(end_time, 'isoformat') else str(end_time)

    payload = {
        'subject': subject,
        'start': {
            'dateTime': start_str,
            'timeZone': 'UTC',
        },
        'end': {
            'dateTime': end_str,
            'timeZone': 'UTC',
        },
    }

    if body:
        content_type = 'HTML' if ('<' in body and '>' in body) else 'Text'
        payload['body'] = {
            'contentType': content_type,
            'content': body,
        }

    if location:
        payload['location'] = {
            'displayName': location,
        }

    response = requests.post(
        f"{GRAPH_API_BASE}/me/events",
        headers={
            'Authorization': f"Bearer {access_token}",
            'Content-Type': 'application/json',
        },
        json=payload,
        timeout=15,
    )
    response.raise_for_status()
    return response.json()

