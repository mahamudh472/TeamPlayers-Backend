import logging
from django.contrib.auth.models import AnonymousUser
from django.contrib.auth import get_user_model
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import AccessToken
from urllib.parse import parse_qs

logger = logging.getLogger("notifications.middleware")
User = get_user_model()

@database_sync_to_async
def get_user_from_token(token_string):
    """
    Decodes the JWT token and returns the corresponding User object.
    Returns AnonymousUser if the token is invalid or expired.
    """
    try:
        access_token = AccessToken(token_string)
        user_id = access_token['user_id']
        user = User.objects.get(id=user_id)
        logger.info(f"WebSocket auth success for user_id: {user_id}")
        return user
    except Exception as e:
        logger.error(f"WebSocket auth token validation failed: {e}", exc_info=True)
        return AnonymousUser()

class TokenAuthMiddleware:
    """
    Custom middleware that authenticates users using a JWT token passed via the 'token' query parameter.
    Used for authorizing WebSocket connections.
    """
    def __init__(self, inner):
        self.inner = inner

    async def __call__(self, scope, receive, send):
        # Extract query parameters from WebSocket connection scope
        query_string = scope.get("query_string", b"").decode("utf-8")
        query_params = parse_qs(query_string)
        token_list = query_params.get("token")
        
        logger.info(f"WebSocket connection attempt with query parameters: {query_params}")
        
        if token_list:
            token = token_list[0]
            scope["user"] = await get_user_from_token(token)
        else:
            logger.warning("WebSocket connection attempt missing token parameter")
            scope["user"] = AnonymousUser()
            
        return await self.inner(scope, receive, send)
