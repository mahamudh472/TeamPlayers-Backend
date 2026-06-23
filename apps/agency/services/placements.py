from django.db.models import Q, QuerySet, Count
from apps.agency.models import Agency, Placement

def get_agency_placements(agency: Agency, status_filter: str = None, search_query: str = None) -> QuerySet[Placement]:
    """
    Returns placements for the agency, filtered by candidate status tab and optional search query.
    """
    queryset = Placement.objects.filter(agency=agency, status='placed').select_related(
        'candidate',
        'job',
        'job__client'
    ).order_by('-created_at')

    if status_filter == 'offers':
        queryset = queryset.filter(candidate__status='offered')
    elif status_filter == 'active':
        queryset = queryset.filter(candidate__status='accepted')
    else:
        # Default 'all' returns both offered and accepted candidates
        queryset = queryset.filter(candidate__status__in=['offered', 'accepted'])

    if search_query:
        queryset = queryset.filter(
            Q(candidate__name__icontains=search_query) |
            Q(candidate__email__icontains=search_query) |
            Q(job__title__icontains=search_query) |
            Q(job__client__company__icontains=search_query)
        )

    return queryset

def get_agency_placement_counts(agency: Agency) -> dict:
    """
    Returns counts for All, Offers, and Active placements under the agency.
    """
    counts = Placement.objects.filter(agency=agency, status='placed').aggregate(
        offers=Count('id', filter=Q(candidate__status='offered')),
        active=Count('id', filter=Q(candidate__status='accepted'))
    )
    
    offers_count = counts['offers'] or 0
    active_count = counts['active'] or 0
    all_count = offers_count + active_count
    
    return {
        "all_count": all_count,
        "offers_count": offers_count,
        "active_count": active_count
    }
