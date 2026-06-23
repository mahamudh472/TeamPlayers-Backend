from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from apps.finance.models import Plan
from apps.finance.serializers import PlanSerializer, ClientRevenueSerializer
from apps.finance.services import get_agency_current_subscription, add_client_revenue
from apps.agency.models import Agency, AgencyMember
from apps.agency.services import get_verified_agency

@method_decorator(cache_page(60 * 60 * 24), name='dispatch')
class PlanListView(ListAPIView):
    """
    Public endpoint to retrieve all subscription plans.
    """
    permission_classes = [AllowAny]
    queryset = Plan.objects.all()
    serializer_class = PlanSerializer


class AgencyCurrentPlanView(APIView):
    """
    Retrieves the current plan and active subscription for the agency specified in the X-Agency-ID header.
    Requires user authentication and that the user is an active, accepted member of the agency.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agency_id = request.agency_id
        if not agency_id:
            return Response(
                {"error": "X-Agency-ID header is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Retrieve the agency
        try:
            agency = Agency.objects.get(id=agency_id)
        except (Agency.DoesNotExist, ValueError):
            return Response(
                {"error": "Agency not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Check that the requesting user is a member of the agency
        is_member = AgencyMember.objects.filter(
            agency=agency,
            user=request.user,
            invitation_status='accepted',
            is_active=True
        ).exists()
        
        if not is_member:
            return Response(
                {"error": "You do not have permission to view this agency's plan"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Get current active subscription
        subscription = get_agency_current_subscription(agency.id)
        if not subscription:
            return Response(
                {"plan": None, "subscription": None},
                status=status.HTTP_200_OK
            )

        plan_serializer = PlanSerializer(subscription.plan)
        return Response({
            "subscription": {
                "id": subscription.id,
                "is_active": subscription.is_active,
                "expires_at": subscription.expires_at,
                "payment_status": subscription.payment_status,
                "payment_method": subscription.payment_method,
                "transaction_id": subscription.transaction_id,
                "plan": subscription.plan_snapshot,
            }
        }, status=status.HTTP_200_OK)


class StripeCheckoutSessionView(APIView):
    """
    Creates a Stripe Checkout Session for the agency to subscribe to a plan.
    Requires user authentication and that the user is an owner/admin member of the agency.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        plan_id = request.data.get('plan_id')
        agency_id = request.agency_id

        if not plan_id or not agency_id:
            return Response(
                {"error": "plan_id is required in request body, and X-Agency-ID is required in header"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Retrieve and verify the agency
        try:
            agency = Agency.objects.get(id=agency_id)
        except (Agency.DoesNotExist, ValueError):
            return Response({"error": "Agency not found"}, status=status.HTTP_404_NOT_FOUND)

        # 2. Check user role inside agency (must be owner or admin)
        try:
            member = AgencyMember.objects.get(
                agency=agency,
                user=request.user,
                invitation_status='accepted',
                is_active=True
            )
            if member.role not in ['owner', 'admin']:
                return Response(
                    {"error": "Only agency owners and admins are authorized to purchase subscriptions"},
                    status=status.HTTP_403_FORBIDDEN
                )
        except AgencyMember.DoesNotExist:
            return Response(
                {"error": "You do not have permission to manage this agency's billing"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 3. Retrieve plan
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            return Response({"error": "Plan not found"}, status=status.HTTP_404_NOT_FOUND)

        # 4. Create session
        from django.conf import settings
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000") or "http://localhost:3000"
        frontend_url = frontend_url.rstrip("/")

        success_url = f"{frontend_url}/payment/success?session_id={{CHECKOUT_SESSION_ID}}"
        cancel_url = f"{frontend_url}/payment/cancel"

        try:
            from apps.finance.services import create_checkout_session
            session_data = create_checkout_session(
                user=request.user,
                agency=agency,
                plan=plan,
                success_url=success_url,
                cancel_url=cancel_url
            )
            return Response(session_data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response(
                {"error": f"Failed to initiate Stripe Checkout Session: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class StripeBillingPortalView(APIView):
    """
    Creates a Stripe Customer Portal session for the agency to manage billing, view invoices, or cancel/update subscriptions.
    Requires user authentication and that the user is an owner/admin member of the agency.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        agency_id = request.agency_id

        if not agency_id:
            return Response(
                {"error": "X-Agency-ID header is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # 1. Retrieve and verify the agency
        try:
            agency = Agency.objects.get(id=agency_id)
        except (Agency.DoesNotExist, ValueError):
            return Response({"error": "Agency not found"}, status=status.HTTP_404_NOT_FOUND)

        # 2. Check user role inside agency (must be owner or admin)
        try:
            member = AgencyMember.objects.get(
                agency=agency,
                user=request.user,
                invitation_status='accepted',
                is_active=True
            )
            if member.role not in ['owner', 'admin']:
                return Response(
                    {"error": "Only agency owners and admins are authorized to manage billing"},
                    status=status.HTTP_403_FORBIDDEN
                )
        except AgencyMember.DoesNotExist:
            return Response(
                {"error": "You do not have permission to manage this agency's billing"},
                status=status.HTTP_403_FORBIDDEN
            )

        # 3. Create billing portal session
        from django.conf import settings
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:3000") or "http://localhost:3000"
        frontend_url = frontend_url.rstrip("/")
        return_url = f"{frontend_url}/billing"

        try:
            from apps.finance.services import create_billing_portal_session
            portal_url = create_billing_portal_session(
                user=request.user,
                return_url=return_url
            )
            return Response({"url": portal_url}, status=status.HTTP_200_OK)
        except ValueError as ve:
            return Response({"error": str(ve)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response(
                {"error": f"Failed to initiate Stripe Billing Portal: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


from django.views.decorators.csrf import csrf_exempt
from djstripe.views import ProcessWebhookView
from djstripe.models import WebhookEndpoint

@method_decorator(csrf_exempt, name="dispatch")
class StripeWebhookView(ProcessWebhookView):
    """
    Custom Stripe Webhook View that automatically maintains a local
    WebhookEndpoint in the database, mapping to settings.DJSTRIPE_WEBHOOK_SECRET.
    Allows easy local testing with Stripe CLI forwarding to a clean url.
    """
    def post(self, request, *args, **kwargs):
        from django.conf import settings
        secret = getattr(settings, "DJSTRIPE_WEBHOOK_SECRET", "") or ""

        # Retrieve or construct a default WebhookEndpoint for local development
        endpoint, created = WebhookEndpoint.objects.get_or_create(
            djstripe_uuid="12345678-1234-1234-1234-123456789012",
            defaults={
                "id": "we_local_test",
                "url": "http://localhost:8000/api/v1/finance/stripe/webhook/",
                "secret": secret,
                "livemode": False,
                "status": "enabled",
                "enabled_events": ["*"],
            }
        )

        # Update key secret dynamically if changed in local settings/.env
        if endpoint.secret != secret:
            endpoint.secret = secret
            endpoint.save()

        return super().post(request, uuid="12345678-1234-1234-1234-123456789012")


class ClientRevenueCreateView(APIView):
    """
    API endpoint to record client revenue.
    Requires user authentication, active agency membership, and valid client.
    Headers:
        X-Agency-ID: ID of the active agency.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, client_id):
        agency_id = request.agency_id
        agency = get_verified_agency(request.user, agency_id)

        serializer = ClientRevenueSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        revenue = add_client_revenue(
            agency=agency,
            user=request.user,
            client_id=client_id,
            amount=serializer.validated_data['amount']
        )

        response_serializer = ClientRevenueSerializer(revenue)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


