class AgencyMiddleware:
    """
    Middleware that extracts the X-Agency-ID header from the request.
    Sets request.agency_id to the header value if present, otherwise to None.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # In Django, request.headers supports case-insensitive retrieval.
        # Falls back to request.META for compatibility.
        agency_id = request.headers.get('X-Agency-ID') or request.META.get('HTTP_X_AGENCY_ID')
        
        # Bind the agency_id to the request object
        request.agency_id = agency_id
        
        response = self.get_response(request)
        return response
