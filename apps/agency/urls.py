from django.urls import path
from .views import UserAgencyListView

urlpatterns = [
    path('', UserAgencyListView.as_view(), name='user_agency_list'),
]
