from django.urls import path
from .views import (
    UserAgencyListView,
    LeadListView,
    LeadDetailView,
    LeadAddNoteView,
    LeadWebhookIngestView,
    LeadChangeStatusView,
    ClientListView,
    ClientDetailView,
    JobListView,
    JobDetailView,
    ClientJobsListView,
    ClientActivityListView,
    ClientNotesView,
    CandidateListView,
    CandidateDetailView,
    CandidateNotesView,
    JobCandidatesListView,
    CandidateShortlistView,
    CandidateInterviewMeetingView,
    CandidateOfferSendView,
    CandidateAcceptView,
    CandidateRejectView
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
    path('clients/<int:pk>/jobs/', ClientJobsListView.as_view(), name='client_jobs_list'),
    path('clients/<int:pk>/activities/', ClientActivityListView.as_view(), name='client_activity_list'),
    path('clients/<int:pk>/notes/', ClientNotesView.as_view(), name='client_notes'),

    path('jobs/', JobListView.as_view(), name='job_list'),
    path('jobs/<int:pk>/', JobDetailView.as_view(), name='job_detail'),
    path('jobs/<int:pk>/candidates/', JobCandidatesListView.as_view(), name='job_candidates_list'),

    path('candidates/', CandidateListView.as_view(), name='candidate_list'),
    path('candidates/<int:pk>/', CandidateDetailView.as_view(), name='candidate_detail'),
    path('candidates/<int:pk>/notes/', CandidateNotesView.as_view(), name='candidate_notes'),
    path('candidates/<int:pk>/shortlist/', CandidateShortlistView.as_view(), name='candidate_shortlist'),
    path('candidates/<int:pk>/meeting/', CandidateInterviewMeetingView.as_view(), name='candidate_meeting'),
    path('candidates/<int:pk>/offer/', CandidateOfferSendView.as_view(), name='candidate_offer_send'),
    path('candidates/<int:pk>/accept/', CandidateAcceptView.as_view(), name='candidate_accept'),
    path('candidates/<int:pk>/reject/', CandidateRejectView.as_view(), name='candidate_reject'),
]



