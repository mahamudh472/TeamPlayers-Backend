from django.db.models import Sum, Q
from django.utils import timezone
from datetime import timedelta
from apps.agency.models import Agency, Job, Candidate, Placement, CandidateMeeting
from apps.finance.models import ClientRevenue, Subscription

def calculate_trend_percentage(current: float, previous: float) -> str:
    """
    Calculates the trend percentage format (e.g. +12% or -5%).
    Handles zero values gracefully.
    """
    if previous == 0:
        if current > 0:
            return "+100%"
        return "0%"
    
    diff = current - previous
    pct = (diff / previous) * 100
    sign = "+" if pct > 0 else ""
    return f"{sign}{round(pct)}%"

def get_dashboard_data(agency: Agency) -> dict:
    """
    Computes all recruitment dashboard statistics, trends, charts, and tables for the given agency.
    """
    now = timezone.now()
    current_month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # Calculate last month's date bounds
    prev_month_date = current_month_start - timedelta(days=1)
    last_month_start = prev_month_date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    
    # 1. Header Card Metrics
    
    # Active Jobs (Open)
    active_jobs_current = Job.objects.filter(agency=agency, status='open').count()
    active_jobs_prev = Job.objects.filter(agency=agency, status='open', created_at__lt=current_month_start).count()
    active_jobs_trend = calculate_trend_percentage(active_jobs_current, active_jobs_prev)
    
    # Total Candidates
    total_candidates_current = Candidate.objects.filter(agency=agency).count()
    total_candidates_prev = Candidate.objects.filter(agency=agency, applied_at__lt=current_month_start).count()
    total_candidates_trend = calculate_trend_percentage(total_candidates_current, total_candidates_prev)
    
    # Active Clients
    active_clients_current = Client = agency.clients.filter(is_active=True).count()
    active_clients_prev = agency.clients.filter(is_active=True, created_at__lt=current_month_start).count()
    active_clients_trend = calculate_trend_percentage(active_clients_current, active_clients_prev)
    
    # Placements (MTD)
    placements_current = Placement.objects.filter(agency=agency, status='placed', created_at__gte=current_month_start).count()
    placements_prev = Placement.objects.filter(
        agency=agency, 
        status='placed', 
        created_at__gte=last_month_start, 
        created_at__lt=current_month_start
    ).count()
    placements_trend = calculate_trend_percentage(placements_current, placements_prev)
    
    # 2. Revenue Overview
    
    # Total Revenue YTD
    ytd_start = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    total_revenue_ytd = ClientRevenue.objects.filter(agency=agency, created_at__gte=ytd_start).aggregate(total=Sum('amount'))['total'] or 0.0
    total_revenue_ytd = float(total_revenue_ytd)
    
    # Revenue YTD Trend vs Same Period Last Year
    last_year_ytd_start = ytd_start.replace(year=ytd_start.year - 1)
    last_year_ytd_end = now.replace(year=now.year - 1)
    prev_revenue_ytd = ClientRevenue.objects.filter(
        agency=agency, 
        created_at__gte=last_year_ytd_start, 
        created_at__lte=last_year_ytd_end
    ).aggregate(total=Sum('amount'))['total'] or 0.0
    prev_revenue_ytd = float(prev_revenue_ytd)
    revenue_ytd_trend = calculate_trend_percentage(total_revenue_ytd, prev_revenue_ytd)
    
    # Determine currency symbol
    subscription = Subscription.objects.filter(agency=agency, is_active=True).select_related('plan').first()
    currency = "GBP"
    if subscription and subscription.plan:
        currency = subscription.plan.currency
    
    currency_map = {
        "USD": "$",
        "EUR": "€",
        "GBP": "£"
    }
    currency_symbol = currency_map.get(currency, "£")
    
    # Generate last 6 months (safely avoiding day math skips)
    months_list = []
    curr_year = now.year
    curr_month = now.month
    for i in range(5, -1, -1):
        month_idx = curr_month - 1 - i
        year_offset = month_idx // 12
        m = (month_idx % 12) + 1
        y = curr_year + year_offset
        month_start = now.replace(year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0)
        months_list.append(month_start)
        
    revenue_monthly_data = []
    pipeline_monthly_data = []
    
    for month_start in months_list:
        if month_start.month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1)
            
        # Revenue per month
        monthly_rev = ClientRevenue.objects.filter(
            agency=agency, 
            created_at__gte=month_start, 
            created_at__lt=next_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0.0
        
        # Pipeline Load (applications count in this month)
        monthly_load = Candidate.objects.filter(
            agency=agency,
            applied_at__gte=month_start,
            applied_at__lt=next_month_start
        ).count()
        
        month_label = month_start.strftime("%b")
        revenue_monthly_data.append({
            "month": month_label,
            "revenue": float(monthly_rev)
        })
        pipeline_monthly_data.append({
            "month": month_label,
            "pipeline_load": monthly_load
        })
        
    # 3. Active Positions (Open Jobs Trend)
    open_jobs_count = Job.objects.filter(agency=agency, status='open').count()
    open_jobs_prev = Job.objects.filter(agency=agency, status='open', created_at__lt=current_month_start).count()
    open_jobs_trend = calculate_trend_percentage(open_jobs_count, open_jobs_prev)
    
    # 4. Upcoming Interviews
    upcoming_meetings = CandidateMeeting.objects.filter(
        agency=agency,
        meeting_time__gte=now,
        meeting_time__lte=now + timedelta(days=7),
        status__in=['scheduled', 'pending']
    ).select_related('candidate', 'candidate__job').order_by('meeting_time')
    
    upcoming_interviews_data = []
    for meeting in upcoming_meetings:
        upcoming_interviews_data.append({
            "id": meeting.id,
            "candidate_name": meeting.candidate.name,
            "job_title": meeting.candidate.job.title if meeting.candidate.job else "",
            "meeting_time": meeting.meeting_time.isoformat(),
            "formatted_meeting_time": meeting.meeting_time.strftime("%d/%m/%Y at %H:%M")
        })
        
    # 5. Hot Candidates (Top 5 matched candidates)
    candidates = Candidate.objects.filter(agency=agency).select_related('job').prefetch_related('ai_analysis')
    hot_candidates_data = []
    for cand in candidates:
        analysis = cand.ai_analysis.order_by('-created_at').first()
        if analysis:
            match_percentage = analysis.overall_match_percentage
            # Scale to 0-100 if stored as 0.0-1.0
            if 0.0 < match_percentage <= 1.0:
                match_percentage *= 100
            hot_candidates_data.append({
                "id": cand.id,
                "name": cand.name,
                "job_title": cand.job.title if cand.job else "",
                "match_percentage": round(match_percentage)
            })
            
    hot_candidates_data.sort(key=lambda x: x["match_percentage"], reverse=True)
    hot_candidates_data = hot_candidates_data[:5]
    
    # 6. Pipeline Health
    pipeline_health = {
        "applications": Candidate.objects.filter(agency=agency, status='new').count(),
        "shortlisted": Candidate.objects.filter(agency=agency, status='shortlisted').count(),
        "interview_stage": Candidate.objects.filter(agency=agency, status='interviewing').count(),
        "placed": Placement.objects.filter(agency=agency, status='placed').count()
    }
    
    return {
        "active_jobs": {
            "value": active_jobs_current,
            "trend": active_jobs_trend
        },
        "total_candidates": {
            "value": total_candidates_current,
            "trend": total_candidates_trend
        },
        "active_clients": {
            "value": active_clients_current,
            "trend": active_clients_trend
        },
        "placements_mtd": {
            "value": placements_current,
            "trend": placements_trend
        },
        "revenue_overview": {
            "total_revenue_ytd": total_revenue_ytd,
            "currency_symbol": currency_symbol,
            "trend_ytd": revenue_ytd_trend,
            "monthly_data": revenue_monthly_data
        },
        "active_positions": {
            "open_jobs_count": open_jobs_count,
            "trend": open_jobs_trend,
            "monthly_data": pipeline_monthly_data
        },
        "upcoming_interviews": upcoming_interviews_data,
        "hot_candidates": hot_candidates_data,
        "pipeline_health": pipeline_health
    }
