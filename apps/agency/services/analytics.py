from datetime import timedelta
from django.utils import timezone
from django.db.models import Sum, Count, Avg, Q
from apps.agency.models import Agency, Job, Candidate, Placement, CandidateMeeting
from apps.finance.models import ClientRevenue, Subscription

def get_date_range_bounds(range_param: str) -> tuple[timezone.datetime | None, timezone.datetime]:
    """
    Returns the start date and end date bounds for the query based on range parameter.
    """
    now = timezone.now()
    if range_param == 'last_month':
        return now - timedelta(days=30), now
    elif range_param == 'last_3_months':
        return now - timedelta(days=90), now
    elif range_param == 'last_year':
        return now - timedelta(days=365), now
    elif range_param == 'all_time':
        return None, now
    # Default to last_year
    return now - timedelta(days=365), now

def get_analytics_data(agency: Agency, range_param: str = 'last_year') -> dict:
    """
    Aggregates comprehensive performance insights for the given agency and time range.
    """
    start_date, end_date = get_date_range_bounds(range_param)
    now = timezone.now()

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

    # ==========================================
    # 1. OVERVIEW DATA
    # ==========================================
    
    # Placement Rate
    placements_qs = Placement.objects.filter(agency=agency, status='placed')
    jobs_qs = Job.objects.filter(agency=agency)
    if start_date:
        placements_qs = placements_qs.filter(created_at__gte=start_date)
        jobs_qs = jobs_qs.filter(created_at__gte=start_date)
    
    total_jobs = jobs_qs.count()
    placed_count = placements_qs.count()
    placement_rate = round((placed_count / total_jobs) * 100, 1) if total_jobs > 0 else 0.0

    # Avg Days to Fill
    days_list = [max(0, (p.created_at - p.job.created_at).days) for p in placements_qs.select_related('job') if p.job]
    avg_days_to_fill = round(sum(days_list) / len(days_list)) if days_list else 0

    # Active Pipelines (point-in-time or filtered open jobs)
    active_pipelines_qs = Job.objects.filter(agency=agency, status='open')
    if start_date:
        active_pipelines_qs = active_pipelines_qs.filter(created_at__gte=start_date)
    active_pipelines = active_pipelines_qs.count()

    # Interviews Booked
    interviews_qs = CandidateMeeting.objects.filter(agency=agency).exclude(status='cancelled')
    if start_date:
        interviews_qs = interviews_qs.filter(meeting_time__gte=start_date)
    interviews_booked = interviews_qs.count()

    # Trend Chart (Revenue & Placements)
    # Determine how many months to show: 6 for last_month/last_3_months, 12 for last_year/all_time
    months_count = 12 if range_param in ['last_year', 'all_time'] else 6
    months_list = []
    curr_year = now.year
    curr_month = now.month
    for i in range(months_count - 1, -1, -1):
        month_idx = curr_month - 1 - i
        year_offset = month_idx // 12
        m = (month_idx % 12) + 1
        y = curr_year + year_offset
        month_start = now.replace(year=y, month=m, day=1, hour=0, minute=0, second=0, microsecond=0)
        months_list.append(month_start)

    trend_data = []
    for month_start in months_list:
        if month_start.month == 12:
            next_month_start = month_start.replace(year=month_start.year + 1, month=1)
        else:
            next_month_start = month_start.replace(month=month_start.month + 1)
            
        # Revenue
        monthly_rev = ClientRevenue.objects.filter(
            agency=agency, 
            created_at__gte=month_start, 
            created_at__lt=next_month_start
        ).aggregate(total=Sum('amount'))['total'] or 0.0

        # Placements count
        monthly_placements = Placement.objects.filter(
            agency=agency,
            status='placed',
            created_at__gte=month_start,
            created_at__lt=next_month_start
        ).count()
        
        trend_data.append({
            "month": month_start.strftime("%b"),
            "revenue": float(monthly_rev),
            "placements": monthly_placements
        })

    # Pipeline Distribution (Candidate flow through stages)
    candidates_qs = Candidate.objects.filter(agency=agency)
    if start_date:
        candidates_qs = candidates_qs.filter(applied_at__gte=start_date)
    
    pipeline_counts = candidates_qs.values('status').annotate(count=Count('id'))
    pipeline_distribution = {
        "new": 0,
        "shortlisted": 0,
        "interviewing": 0,
        "offered": 0,
        "accepted": 0,
        "rejected": 0
    }
    for item in pipeline_counts:
        status_name = item['status']
        if status_name in pipeline_distribution:
            pipeline_distribution[status_name] = item['count']

    # Placements by Industry
    industry_data = (
        placements_qs
        .filter(job__client__isnull=False)
        .values('job__client__industry')
        .annotate(count=Count('id'))
        .order_by('-count')
    )
    placements_by_industry = []
    for item in industry_data:
        industry_name = item['job__client__industry'] or "Other"
        placements_by_industry.append({
            "industry": industry_name,
            "count": item['count']
        })

    overview = {
        "placement_rate": placement_rate,
        "avg_days_to_fill": avg_days_to_fill,
        "active_pipelines": active_pipelines,
        "interviews_booked": interviews_booked,
        "revenue_placements_trend": trend_data,
        "pipeline_distribution": pipeline_distribution,
        "placements_by_industry": placements_by_industry,
        "currency_symbol": currency_symbol
    }

    # ==========================================
    # 2. CLIENTS DATA
    # ==========================================
    clients_qs = agency.clients.all()
    total_clients = clients_qs.count()
    
    clients_list = []
    client_success_rates = []
    for client in clients_qs:
        # Placements count in date range
        client_placements = Placement.objects.filter(job__client=client, status='placed')
        if start_date:
            client_placements = client_placements.filter(created_at__gte=start_date)
        client_placements_count = client_placements.count()

        # Revenue count in date range
        client_rev = ClientRevenue.objects.filter(client=client)
        if start_date:
            client_rev = client_rev.filter(created_at__gte=start_date)
        client_revenue_sum = client_rev.aggregate(total=Sum('amount'))['total'] or 0.0

        # Total jobs count in date range
        client_jobs = Job.objects.filter(client=client)
        if start_date:
            client_jobs = client_jobs.filter(created_at__gte=start_date)
        client_jobs_count = client_jobs.count()

        # Success rate = (placements / total jobs) * 100
        if client_jobs_count > 0:
            success_rate = round((client_placements_count / client_jobs_count) * 100, 1)
        else:
            success_rate = 0.0
        client_success_rates.append(success_rate)

        # Active jobs
        client_active_jobs = Job.objects.filter(client=client, status='open').count()

        clients_list.append({
            "id": client.id,
            "company": client.company,
            "industry": client.industry or "Other",
            "active_jobs": client_active_jobs,
            "placements_count": client_placements_count,
            "revenue": float(client_revenue_sum),
            "success_rate": success_rate
        })
    
    # Sort clients by revenue descending
    clients_list.sort(key=lambda x: x["revenue"], reverse=True)

    # Average success rate across all clients
    avg_client_success_rate = round(sum(client_success_rates) / len(client_success_rates), 1) if client_success_rates else 0.0
    
    # Average jobs per client = total jobs under agency / total clients
    avg_jobs_per_client = round(total_jobs / total_clients, 1) if total_clients > 0 else 0.0

    clients_data = {
        "total_clients": total_clients,
        "avg_jobs_per_client": avg_jobs_per_client,
        "avg_client_success_rate": avg_client_success_rate,
        "top_clients": clients_list
    }

    # ==========================================
    # 3. CANDIDATES DATA
    # ==========================================
    candidates_list_qs = Candidate.objects.filter(agency=agency)
    if start_date:
        candidates_list_qs = candidates_list_qs.filter(applied_at__gte=start_date)

    from collections import Counter
    skills_counter = Counter()
    experience_groups = {"Entry (0-2 yrs)": 0, "Mid (3-5 yrs)": 0, "Senior (6+ yrs)": 0}

    for cand in candidates_list_qs:
        if isinstance(cand.skills, list):
            for skill in cand.skills:
                if skill:
                    skills_counter[skill.strip().title()] += 1
        
        exp = cand.experience or 0
        if exp <= 2:
            experience_groups["Entry (0-2 yrs)"] += 1
        elif exp <= 5:
            experience_groups["Mid (3-5 yrs)"] += 1
        else:
            experience_groups["Senior (6+ yrs)"] += 1

    top_skills = [{"skill": k, "count": v} for k, v in skills_counter.most_common(15)]
    experience_dist = [{"level": k, "count": v} for k, v in experience_groups.items()]

    # Top skill match: "Python (3 profiles)"
    if top_skills:
        most_common_skill = top_skills[0]
        top_skill_match = f"{most_common_skill['skill']} ({most_common_skill['count']} profiles)"
    else:
        top_skill_match = "N/A"

    # Primary experience bracket
    primary_experience_bracket = max(experience_groups, key=experience_groups.get)
    if sum(experience_groups.values()) == 0:
        primary_experience_bracket = "N/A"

    candidates_data = {
        "total_applications": candidates_list_qs.count(),
        "top_skill_match": top_skill_match,
        "primary_experience_bracket": primary_experience_bracket,
        "experience_distribution": experience_dist,
        "top_skills": top_skills
    }

    # ==========================================
    # 4. RECRUITERS DATA
    # ==========================================
    members = agency.members.filter(is_active=True).select_related('user')
    recruiters_list = []
    for member in members:
        user = member.user
        
        # Placements count in range
        recruiter_placements = Placement.objects.filter(agency=agency, user=user, status='placed')
        if start_date:
            recruiter_placements = recruiter_placements.filter(created_at__gte=start_date)
        recruiter_placements_count = recruiter_placements.count()

        # Interviews count in range
        recruiter_interviews = CandidateMeeting.objects.filter(agency=agency, user=user).exclude(status='cancelled')
        if start_date:
            recruiter_interviews = recruiter_interviews.filter(meeting_time__gte=start_date)
        recruiter_interviews_count = recruiter_interviews.count()

        recruiters_list.append({
            "id": user.id,
            "name": user.full_name or user.email,
            "role": member.role,
            "placements_count": recruiter_placements_count,
            "interviews_count": recruiter_interviews_count
        })
    recruiters_list.sort(key=lambda x: x["placements_count"], reverse=True)

    # ==========================================
    # 5. AI PERFORMANCE DATA
    # ==========================================
    analyses_qs = agency.candidate_ai_analysis.all()
    if start_date:
        analyses_qs = analyses_qs.filter(created_at__gte=start_date)

    avg_match_score = analyses_qs.aggregate(avg=Avg('overall_match_percentage'))['avg'] or 0.0
    if 0.0 < avg_match_score <= 1.0:
        avg_match_score *= 100
    avg_match = round(avg_match_score, 1)

    placed_avg = analyses_qs.filter(candidate__status='accepted').aggregate(avg=Avg('overall_match_percentage'))['avg'] or 0.0
    if 0.0 < placed_avg <= 1.0:
        placed_avg *= 100
    placed_avg_match = round(placed_avg, 1)

    rejected_avg = analyses_qs.filter(candidate__status='rejected').aggregate(avg=Avg('overall_match_percentage'))['avg'] or 0.0
    if 0.0 < rejected_avg <= 1.0:
        rejected_avg *= 100
    rejected_avg_match = round(rejected_avg, 1)

    ai_performance = {
        "avg_overall_match_score": avg_match,
        "avg_placed_match_score": placed_avg_match,
        "avg_rejected_match_score": rejected_avg_match
    }

    return {
        "overview": overview,
        "clients": clients_data,
        "candidates": candidates_data,
        "recruiters": recruiters_list,
        "ai_performance": ai_performance
    }
