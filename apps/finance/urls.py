from django.urls import path, include
from .views import (
    PlanListView,
    AgencyCurrentPlanView,
    StripeCheckoutSessionView,
    StripeBillingPortalView,
    StripeWebhookView,
    ClientRevenueCreateView
)

urlpatterns = [
    path('plans/', PlanListView.as_view(), name='plan_list'),
    path('agency-plan/', AgencyCurrentPlanView.as_view(), name='agency_current_plan'),
    path('checkout/', StripeCheckoutSessionView.as_view(), name='stripe_checkout'),
    path('billing-portal/', StripeBillingPortalView.as_view(), name='stripe_billing_portal'),
    path('stripe/webhook/', StripeWebhookView.as_view(), name='stripe_webhook'),
    path('stripe/', include('djstripe.urls', namespace="djstripe")),
    path('clients/<int:client_id>/revenue/', ClientRevenueCreateView.as_view(), name='add_client_revenue'),
]

