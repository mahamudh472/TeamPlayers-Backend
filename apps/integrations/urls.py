from django.urls import path
from . import views

urlpatterns = [
    path('', views.IntegrationListView.as_view(), name='integration_list'),
    path('zoom/connect/', views.ZoomConnectView.as_view(), name='zoom_connect'),
    path('zoom/callback/', views.ZoomCallbackView.as_view(), name='zoom_callback'),
    path('zoom/disconnect/', views.ZoomDisconnectView.as_view(), name='zoom_disconnect'),
    path('zoom/meetings/create/', views.ZoomCreateMeetingView.as_view(), name='zoom_create_meeting'),
]
