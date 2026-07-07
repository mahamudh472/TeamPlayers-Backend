from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response

class NotificationPagination(PageNumberPagination):
    """
    Standard page number pagination class for notifications.
    Allows clients to override page_size using the query param 'page_size'.
    """
    page_size = 15
    page_size_query_param = 'page_size'
    max_page_size = 100

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'next': self.get_next_link(),
            'previous': self.get_previous_link(),
            'results': data
        })
