from django.urls import path
from .views import (
    UserAgencyListView,
    LeadListView,
    LeadDetailView,
    LeadAddNoteView,
    LeadWebhookIngestView,
    LeadChangeStatusView,
    ClientListView,
    ClientDetailView
)

urlpatterns = [
    path('', UserAgencyListView.as_view(), name='user_agency_list'),
    path('leads/', LeadListView.as_view(), name='lead_list'),
    path('leads/<int:pk>/', LeadDetailView.as_view(), name='lead_detail'),
    path('leads/<int:pk>/notes/', LeadAddNoteView.as_view(), name='lead_add_note'),
    path('leads/<int:pk>/status/', LeadChangeStatusView.as_view(), name='lead_change_status'),
    path('webhooks/leads/', LeadWebhookIngestView.as_view(), name='lead_webhook_ingest'),
    
    path('clients/', ClientListView.as_view(), name='client_list'),
    path('clients/<int:pk>/', ClientDetailView.as_view(), name='client_detail'),
]
