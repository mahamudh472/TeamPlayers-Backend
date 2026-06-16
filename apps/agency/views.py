from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from apps.agency.services import get_user_agencies
from apps.agency.serializers import UserAgencySerializer

class UserAgencyListView(APIView):
    """
    API endpoint to list agencies and roles for the authenticated user.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        agencies = get_user_agencies(request.user)
        serializer = UserAgencySerializer(agencies, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)
