from typing import Dict
from django.db.models import Count, QuerySet
from apps.agency.models import Agency, Leads, Note, Activity
from apps.accounts.models import User
from rest_framework.exceptions import NotFound

def get_agency_leads(agency: Agency, status_filter: str = None) -> QuerySet[Leads]:
    """
    Returns leads for the agency, optionally filtered by status.
    """
    queryset = Leads.objects.filter(agency=agency).order_by('-created_at')
    if status_filter:
        queryset = queryset.filter(status=status_filter)
    return queryset

def get_agency_lead_by_id(agency: Agency, lead_id: int) -> Leads:
    """
    Returns a single lead for the agency, or raises NotFound.
    """
    try:
        return Leads.objects.get(agency=agency, id=lead_id)
    except (Leads.DoesNotExist, ValueError):
        raise NotFound("Lead not found")

def get_lead_notes(agency: Agency, lead_id: int) -> QuerySet[Note]:
    """
    Returns notes associated with the lead for the agency.
    """
    return Note.objects.filter(
        agency=agency,
        model='lead',
        model_id=lead_id
    ).select_related('user').order_by('-created_at')

def get_agency_lead_status_counts(agency: Agency) -> Dict[str, int]:
    """
    Returns counts of leads grouped by status.
    """
    status_counts = (
        Leads.objects.filter(agency=agency)
        .values('status')
        .annotate(count=Count('id'))
    )
    # Get all potential choices from the model to default to 0
    choices = [choice[0] for choice in Leads.status.field.choices]
    counts = {choice: 0 for choice in choices}
    
    for item in status_counts:
        status_val = item['status']
        if status_val in counts:
            counts[status_val] = item['count']
            
    return counts

def add_note_to_lead(agency: Agency, user: User, lead_id: int, content: str) -> Note:
    """
    Verifies lead existence and adds a note to it.
    """
    # Verify the lead exists in the agency
    lead = get_agency_lead_by_id(agency, lead_id)
    
    # Create the note
    note = Note.objects.create(
        content=content,
        model='lead',
        model_id=lead.id,
        user=user,
        agency=agency
    )
    return note


def ingest_bulk_leads(agency: Agency, leads_data: list[dict], user=None) -> list[Leads]:
    """
    Creates multiple Lead objects for a given agency from list data.
    """
    created_leads = []
    for data in leads_data:
        lead = Leads.objects.create(
            company=data.get('company'),
            contact_person=data.get('contact_person'),
            contact_email=data.get('contact_email'),
            contact_phone=data.get('contact_phone'),
            location=data.get('location'),
            industry=data.get('industry'),
            source=data.get('source'),
            priority=data.get('priority', 'low'),
            status=data.get('status', 'new'),
            agency=agency
        )
        created_leads.append(lead)
        Activity.objects.create(
            model='lead',
            model_id=lead.id,
            agency=agency,
            user=user,
            summary=f"Ingested lead for {lead.company} via webhook"
        )
    return created_leads


def update_lead_status(agency: Agency, lead_id: int, status_val: str, user=None) -> Leads:
    """
    Verifies lead existence and updates its status.
    """
    from rest_framework.exceptions import ValidationError
    
    lead = get_agency_lead_by_id(agency, lead_id)
    
    valid_statuses = [choice[0] for choice in Leads.status.field.choices]
    if status_val not in valid_statuses:
        raise ValidationError(f"Invalid status choice. Must be one of: {', '.join(valid_statuses)}")
        
    lead.status = status_val
    lead.save()

    Activity.objects.create(
        model='lead',
        model_id=lead.id,
        agency=agency,
        user=user,
        summary=f"Changed status of lead {lead.company} to {status_val.title()}"
    )

    return lead


