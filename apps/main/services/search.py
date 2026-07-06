from django.db.models import Q
from apps.agency.models import Leads, Candidate, Client, Job

def get_leads_search_result(query, agency):
    """
    Search leads for a specific agency.
    """
    return Leads.objects.filter(agency=agency).filter(
        Q(company__icontains=query) |
        Q(contact_person__icontains=query) |
        Q(contact_email__icontains=query) |
        Q(location__icontains=query) |
        Q(industry__icontains=query)
    )

def get_candidates_search_result(query, agency):
    """
    Search candidates for a specific agency.
    """
    return Candidate.objects.filter(agency=agency).filter(
        Q(name__icontains=query) |
        Q(email__icontains=query) |
        Q(skills__icontains=query) |
        Q(location__icontains=query)
    )

def get_clients_search_result(query, agency):
    """
    Search clients for a specific agency.
    """
    return Client.objects.filter(agency=agency).filter(
        Q(company__icontains=query) |
        Q(contact_person__icontains=query) |
        Q(contact_email__icontains=query) |
        Q(location__icontains=query) |
        Q(industry__icontains=query)
    )

def get_jobs_search_result(query, agency):
    """
    Search jobs for a specific agency.
    """
    return Job.objects.filter(agency=agency).filter(
        Q(title__icontains=query) |
        Q(description__icontains=query) |
        Q(location__icontains=query) |
        Q(client__company__icontains=query) |
        Q(client__industry__icontains=query)
    )

def sanitize_results(results, result_source):
    """
    Sanitize the search results to return a unified format.
    """
    sanitized_results = []
    for result in results:
        sanitized_result = {
            "object_id": result.id,
            "description": "",
            "result_source": result_source
        }
        
        if result_source in ("leads", "clients"):
            sanitized_result["title"] = getattr(result, 'company', '')
            sanitized_result["description"] = getattr(result, 'industry', '') or ''
        elif result_source == "candidates":
            sanitized_result["title"] = getattr(result, 'name', '')
            sanitized_result["description"] = getattr(result.job, 'title', '') if getattr(result, 'job', None) else ''
        elif result_source == "jobs":
            sanitized_result["title"] = getattr(result, 'title', '')
            sanitized_result["description"] = getattr(result.client, 'company', '') if getattr(result, 'client', None) else ''

        sanitized_results.append(sanitized_result)
    return sanitized_results

def perform_search(query, agency):
    """
    Perform a search across leads, candidates, clients, and jobs for a specific agency.

    Args:
        query (str): The search query.
        agency (Agency): The agency to filter results by.

    Returns:
        list: A list of sanitized search results.
    """
    results = []
    
    if query and agency:
        leads_results = get_leads_search_result(query, agency)
        candidates_results = get_candidates_search_result(query, agency)
        clients_results = get_clients_search_result(query, agency)
        jobs_results = get_jobs_search_result(query, agency)

        results.extend(sanitize_results(leads_results, "leads"))
        results.extend(sanitize_results(candidates_results, "candidates"))
        results.extend(sanitize_results(clients_results, "clients"))
        results.extend(sanitize_results(jobs_results, "jobs"))
    
    return results

