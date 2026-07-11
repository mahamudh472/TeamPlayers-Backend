import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger("notifications.consumers")

class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that handles real-time notifications for authenticated users.
    """
    async def connect(self):
        # Retrieve the authenticated user from scope (injected by our TokenAuthMiddleware)
        self.user = self.scope.get("user")
        
        logger.info(f"NotificationConsumer connection attempt. User: {self.user}")
        
        # Reject the connection if user is not authenticated
        if not self.user or self.user.is_anonymous:
            logger.warning("Rejecting WebSocket connection: Anonymous user")
            await self.close(code=4003)  # 4003: Forbidden
            return
            
        # Group name is uniquely identified by the user's UUID primary key
        self.group_name = f"user_{self.user.id}"
        
        logger.info(f"Adding user {self.user.id} to group: {self.group_name}")
        
        # Join user's individual notification group
        try:
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            logger.info(f"Successfully joined channel group: {self.group_name}")
        except Exception as e:
            logger.error(f"Failed to join channel group {self.group_name}: {e}", exc_info=True)
            await self.close(code=1011)  # 1011: Internal Error
            return
        
        await self.accept()
        logger.info(f"WebSocket connection accepted for user: {self.user.id}")

    async def disconnect(self, close_code):
        logger.info(f"WebSocket disconnected for user: {getattr(self, 'user', 'Unknown')}. Code: {close_code}")
        # Leave the notification group on disconnect
        if hasattr(self, "group_name"):
            try:
                await self.channel_layer.group_discard(
                    self.group_name,
                    self.channel_name
                )
                logger.info(f"Successfully discarded channel group: {self.group_name}")
            except Exception as e:
                logger.error(f"Failed to discard channel group {self.group_name}: {e}", exc_info=True)

    async def notification_message(self, event):
        """
        Receives notification events from the channel layer group and forwards them to the client.
        """
        notification = event.get("notification")
        logger.info(f"Forwarding notification to user {self.user.id}: {notification}")
        
        await self.send(text_data=json.dumps({
            "type": "notification",
            "data": notification
        }))
