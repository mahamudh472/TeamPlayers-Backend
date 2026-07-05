from apps.agency.models import Leads, Candidate, Client, Job
from django.db.models import Q

from django.db.models import Q

def get_leads_search_result(query):
    results = Leads.objects.filter(
        Q(company__icontains=query) |
        Q(contact_person__icontains=query) |
        Q(email__icontains=query) |
        Q(location__icontains=query) |
        Q(industry__icontains=query)
    )
    return results

def get_candidates_search_result(query):
    results = Candidate.objects.filter(
        Q(name__icontains=query) |
        Q(email__icontains=query) |
        Q(skills__icontains=query) |
        Q(location__icontains=query)
    )
    return results

def get_clients_search_result(query):
    results = Client.objects.filter(
        Q(compnay__icontains=query) |
        Q(contact_person__icontains=query) |
        Q(contact_email__icontains=query) |
        Q(location__icontains=query) |
        Q(industry__icontains=query)
    )
    return results

def get_jobs_search_result(query):
    results = Job.objects.filter(
        Q(title__icontains=query) |
        Q(description__icontains=query) |
        Q(location__icontains=query) |
        Q(industry__icontains=query)
    )
    return results

def sanetize_results(results, result_source):
    sanitized_results = []
    for result in results:
        sanitized_result = {
            "object_id": result.id,
            "description": getattr(result, 'description', ''),
            "result_source": result_source
        }
        if result_source == "leads" or result_source == "clients":
            sanitized_result["title"] = getattr(result, 'company', '')
            sanitized_result["description"] = getattr(result, 'industry', '')
        elif result_source == "candidates":
            sanitized_result["title"] = getattr(result, 'name', '')
            sanitized_result["description"] = getattr(result, 'job', '')
        elif result_source == "jobs":
            sanitized_result["title"] = getattr(result, 'title', '')
            sanitized_result["description"] = getattr(result, 'company', '')

        sanitized_results.append(sanitized_result)
    return sanitized_results

def perform_search(query):
    """
    Perform a search based on the given query.

    Args:
        query (str): The search query.

    Returns:
        list: A list of search results.
        [
            {
                "object_id": "result item id"
                "title": "Result title",
                "description": "Result description",
                "result_source": "leads/candidates/client/job"

            }
        ]
    """
    results = []
    
    if query:
        leads_results = get_leads_search_result(query)
        candidates_results = get_candidates_search_result(query)
        clients_results = get_clients_search_result(query)
        jobs_results = get_jobs_search_result(query)

        results.extend(sanetize_results(leads_results, "leads"))
        results.extend(sanetize_results(candidates_results, "candidates"))
        results.extend(sanetize_results(clients_results, "clients"))
        results.extend(sanetize_results(jobs_results, "jobs"))
    
    return results
