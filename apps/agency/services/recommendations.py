from django.utils import timezone
from apps.agency.models import Agency, Candidate, Leads, Client, Activity

def get_recommendations_and_hot_candidates(agency: Agency) -> dict:
    """
    Retrieves AI recommendations and hot candidates for the agency,
    filtered and ordered by their matching scores.
    """
    now = timezone.now()
    
    # Pre-fetch candidate analysis to prevent N+1 queries
    candidates = Candidate.objects.filter(
        agency=agency, 
        is_processing=False
    ).select_related('job').prefetch_related('ai_analysis')
    
    recommendations = []
    hot_candidates_list = []
    
    # Process candidate-specific matching scores
    for cand in candidates:
        analysis = cand.ai_analysis.order_by('-created_at').first()
        if not analysis:
            continue
            
        match_percentage = analysis.overall_match_percentage
        # Scale percentage if stored as a fraction
        if 0.0 < match_percentage <= 1.0:
            match_percentage *= 100
        
        match_score = round(match_percentage)
        
        # Add to Hot Candidates
        hot_candidates_list.append({
            "id": cand.id,
            "name": cand.name,
            "role": cand.job.title if cand.job else "",
            "matchScore": match_score,
            "link": f"/dashboard/candidates/{cand.id}"
        })
        
        # Recommendation Type 1: High-match candidate needs follow-up
        if cand.status == 'shortlisted' and match_score >= 90:
            # Determine duration candidate has been shortlisted
            activity = Activity.objects.filter(
                agency=agency,
                model='candidate',
                model_id=cand.id,
                summary__icontains='shortlisted'
            ).order_by('-created_at').first()
            
            if activity:
                days = (now - activity.created_at).days
            else:
                days = (now - cand.applied_at).days
                
            if days < 0:
                days = 0
                
            recommendations.append({
                "id": f"rec-candidate-followup-{cand.id}",
                "type": "alert",
                "title": "High-match candidate needs follow-up",
                "description": f"{cand.name} ({match_score}% match) has been shortlisted for {days} days",
                "actionText": "Schedule Interview",
                "actionLink": f"/dashboard/candidates/{cand.id}?schedule=true"
            })
            
        # Recommendation Type 2: Perfect candidate for role
        elif cand.status == 'new' and match_score >= 90:
            job_title = cand.job.title if cand.job else "role"
            recommendations.append({
                "id": f"rec-candidate-perfect-{cand.id}",
                "type": "check",
                "title": f"Perfect candidate for {job_title} role",
                "description": f"{cand.name} is {match_score}% match - consider fast-tracking",
                "actionText": "Review Now",
                "actionLink": f"/dashboard/candidates/{cand.id}"
            })
            
    # Sort hot candidates by match score in descending order
    hot_candidates_list.sort(key=lambda x: x["matchScore"], reverse=True)
    
    # 2. Recommendations for Leads
    # Query new leads for the agency
    new_leads = Leads.objects.filter(agency=agency, status='new').order_by('-created_at')
    
    # Get active client industries to match against leads
    active_client_industries = set(
        Client.objects.filter(agency=agency, is_active=True, industry__isnull=False)
        .exclude(industry='')
        .values_list('industry', flat=True)
    )
    
    for lead in new_leads:
        # Determine if this lead qualifies as high value
        is_high_value = False
        if lead.priority == 'high':
            is_high_value = True
        elif lead.industry and lead.industry in active_client_industries:
            is_high_value = True
            
        if is_high_value:
            recommendations.append({
                "id": f"rec-lead-{lead.id}",
                "type": "trend",
                "title": "New high-value lead detected",
                "description": f"{lead.company} matches your success profile - similar to your top clients",
                "actionText": "View Lead",
                "actionLink": f"/dashboard/leads"
            })
            
    return {
        "recommendations": recommendations[:5],
        "hot_candidates": hot_candidates_list[:5]
    }
