from django.urls import path
from . import views

urlpatterns = [
    path('', views.NotificationListView.as_view(), name='notification_list'),
    path('<int:notification_id>/read/', views.MarkNotificationReadView.as_view(), name='mark_notification_read'),
    path('read-all/', views.MarkAllNotificationsReadView.as_view(), name='mark_all_notifications_read'),
    path('send-test/', views.SendTestNotificationView.as_view(), name='send_test_notification'),
]
