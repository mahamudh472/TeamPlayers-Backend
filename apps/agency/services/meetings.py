from django.db.models import Q, QuerySet, Count
from django.utils import timezone
from datetime import timedelta
from apps.agency.models import Agency, CandidateMeeting

def get_agency_meetings(agency: Agency, status_filter: str = None, search_query: str = None) -> QuerySet[CandidateMeeting]:
    """
    Returns candidate meetings (interviews) for the agency, optionally filtered by status and search query.
    """
    queryset = CandidateMeeting.objects.filter(agency=agency).select_related(
        'candidate',
        'candidate__job',
        'candidate__job__client'
    ).order_by('-meeting_time')
    
    if status_filter:
        if status_filter == 'upcoming':
            queryset = queryset.filter(status__in=['scheduled', 'pending'])
        elif status_filter == 'completed':
            queryset = queryset.filter(status='completed')
        elif status_filter in ['scheduled', 'pending', 'cancelled']:
            queryset = queryset.filter(status=status_filter)
            
    if search_query:
        queryset = queryset.filter(
            Q(candidate__name__icontains=search_query) |
            Q(candidate__job__title__icontains=search_query) |
            Q(candidate__job__client__company__icontains=search_query)
        )
        
    return queryset

def get_agency_meeting_counts(agency: Agency) -> dict:
    """
    Returns counts for Scheduled, Completed, and This Week's interviews for the agency.
    """
    now = timezone.now()
    start_of_week = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    end_of_week = start_of_week + timedelta(days=7)

    counts = CandidateMeeting.objects.filter(agency=agency).aggregate(
        scheduled=Count('id', filter=Q(status__in=['scheduled', 'pending'])),
        completed=Count('id', filter=Q(status='completed')),
        this_week=Count('id', filter=Q(meeting_time__range=(start_of_week, end_of_week)) & ~Q(status='cancelled'))
    )
    return {
        "scheduled_count": counts['scheduled'] or 0,
        "completed_count": counts['completed'] or 0,
        "this_week_count": counts['this_week'] or 0
    }

def get_agency_meetings_by_month(agency: Agency, year: int, month: int) -> QuerySet[CandidateMeeting]:
    """
    Returns candidate meetings (interviews) for the agency, filtered by specified year and month.
    """
    return CandidateMeeting.objects.filter(
        agency=agency,
        meeting_time__year=year,
        meeting_time__month=month
    ).select_related('candidate', 'candidate__job').order_by('meeting_time')

