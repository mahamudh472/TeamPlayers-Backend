import json
from channels.generic.websocket import AsyncWebsocketConsumer

class NotificationConsumer(AsyncWebsocketConsumer):
    """
    WebSocket consumer that handles real-time notifications for authenticated users.
    """
    async def connect(self):
        # Retrieve the authenticated user from scope (injected by our TokenAuthMiddleware)
        self.user = self.scope.get("user")
        
        # Reject the connection if user is not authenticated
        if not self.user or self.user.is_anonymous:
            await self.close(code=4003)  # 4003: Forbidden
            return
            
        # Group name is uniquely identified by the user's UUID primary key
        self.group_name = f"user_{self.user.id}"
        
        # Join user's individual notification group
        await self.channel_layer.group_add(
            self.group_name,
            self.channel_name
        )
        
        await self.accept()

    async def disconnect(self, close_code):
        # Leave the notification group on disconnect
        if hasattr(self, "group_name"):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )

    async def notification_message(self, event):
        """
        Receives notification events from the channel layer group and forwards them to the client.
        """
        notification = event.get("notification")
        
        await self.send(text_data=json.dumps({
            "type": "notification",
            "data": notification
        }))
