from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from apps.main.serializers import ContactMessageSerializer
from apps.main.services import create_contact_message, search

class ContactMessageCreateView(APIView):
    """
    API endpoint to post/create a contact message.
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = ContactMessageSerializer(data=request.data)
        if serializer.is_valid():
            contact_message = create_contact_message(serializer.validated_data)
            response_serializer = ContactMessageSerializer(contact_message)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class DashboardSearchView(APIView):
    """
    API endpoint to search for dashboard data.
    """
    permission_classes = [AllowAny]

    def get(self, request, *args, **kwargs):
        query = request.query_params.get('query', None)

        if query:
            results = search.perform_search(query)
            return Response(results, status=status.HTTP_200_OK)
        return Response({"error": "Query parameter is required."}, status=status.HTTP_400_BAD_REQUEST)

