from rest_framework.generics import GenericAPIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status
from .serializers import NotificationSerializer
from .paginations import NotificationPagination
from .services.notifications import (
    get_user_notifications,
    mark_notification_as_read,
    mark_all_notifications_as_read,
    create_notification
)

class NotificationListView(GenericAPIView):
    """
    Retrieves a paginated list of notifications for the authenticated user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer
    pagination_class = NotificationPagination

    def get(self, request):
        queryset = get_user_notifications(request.user)
        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MarkNotificationReadView(GenericAPIView):
    """
    Marks a specific notification as read for the authenticated user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def post(self, request, notification_id):
        notification = mark_notification_as_read(request.user, notification_id)
        serializer = self.get_serializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)


class MarkAllNotificationsReadView(GenericAPIView):
    """
    Marks all notifications for the authenticated user as read.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        count = mark_all_notifications_as_read(request.user)
        return Response({
            "message": f"Successfully marked {count} notifications as read",
            "count": count
        }, status=status.HTTP_200_OK)


class SendTestNotificationView(GenericAPIView):
    """
    Sends a real-time test notification to the authenticated user.
    """
    permission_classes = [IsAuthenticated]
    serializer_class = NotificationSerializer

    def post(self, request):
        notification = create_notification(
            user=request.user,
            title="Instant Test Notification",
            message="This is a test notification generated in real-time.",
            notification_type="test_notification",
            source={"type": "test", "id": "test_id"}
        )
        serializer = self.get_serializer(notification)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

