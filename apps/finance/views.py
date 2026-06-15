from rest_framework.views import APIView
from rest_framework.generics import ListAPIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page

from apps.finance.models import Plan
from apps.finance.serializers import PlanSerializer
from apps.finance.services import get_agency_current_subscription
from apps.agency.models import Agency, AgencyMember

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
        # Read header (HTTP_X_AGENCY_ID matches X-Agency-ID / x-agency-id)
        agency_id = request.headers.get('X-Agency-ID') or request.META.get('HTTP_X_AGENCY_ID')
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
            "plan": plan_serializer.data,
            "subscription": {
                "id": subscription.id,
                "is_active": subscription.is_active,
                "expires_at": subscription.expires_at,
                "payment_status": subscription.payment_status,
                "payment_method": subscription.payment_method,
                "transaction_id": subscription.transaction_id,
            }
        }, status=status.HTTP_200_OK)

