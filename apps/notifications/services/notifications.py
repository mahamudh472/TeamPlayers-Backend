from django.db.models import QuerySet
from apps.notifications.models import Notification
from rest_framework.exceptions import NotFound
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync

def get_user_notifications(user) -> QuerySet[Notification]:
    """
    Retrieves all notifications for a specific user, ordered by creation date descending.
    """
    return Notification.objects.filter(user=user).order_by('-created_at')

def create_notification(user, title: str, message: str, notification_type: str, source: dict = None) -> Notification:
    """
    Creates a new notification in the database and broadcasts it via WebSocket.
    """
    if source is None:
        source = {}
        
    notification = Notification.objects.create(
        user=user,
        title=title,
        message=message,
        notification_type=notification_type,
        source=source
    )
    
    # Broadcast to websocket
    broadcast_notification(notification)
    
    return notification

def mark_notification_as_read(user, notification_id: int) -> Notification:
    """
    Marks a single notification as read for the user. Raises NotFound if not found.
    """
    try:
        notification = Notification.objects.get(user=user, id=notification_id)
        if not notification.is_read:
            notification.is_read = True
            notification.save()
        return notification
    except Notification.DoesNotExist:
        raise NotFound("Notification not found")

def mark_all_notifications_as_read(user) -> int:
    """
    Marks all unread notifications as read for the user. Returns count of modified items.
    """
    unread = Notification.objects.filter(user=user, is_read=False)
    count = unread.count()
    if count > 0:
        unread.update(is_read=True)
    return count

def broadcast_notification(notification: Notification):
    """
    Broadcasts the serialized notification payload to the user's specific WebSocket group.
    """
    try:
        channel_layer = get_channel_layer()
        if channel_layer:
            from apps.notifications.serializers import NotificationSerializer
            serializer = NotificationSerializer(notification)
            group_name = f"user_{notification.user.id}"
            
            async_to_sync(channel_layer.group_send)(
                group_name,
                {
                    "type": "notification.message",
                    "notification": serializer.data
                }
            )
    except Exception as e:
        # Gracefully handle situations where channel layer is not running or properly set up
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to broadcast websocket notification: {str(e)}")
