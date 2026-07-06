from django.urls import path
from .views import ContactMessageCreateView, DashboardSearchView

urlpatterns = [
    path('contact/', ContactMessageCreateView.as_view(), name='contact_message_create'),
    path('search/', DashboardSearchView.as_view(), name='dashboard_search'),
]

