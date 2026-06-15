from django.urls import path
from .views import PlanListView, AgencyCurrentPlanView

urlpatterns = [
    path('plans/', PlanListView.as_view(), name='plan_list'),
    path('agency-plan/', AgencyCurrentPlanView.as_view(), name='agency_current_plan'),
]
