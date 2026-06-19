from django.db.models import Q, QuerySet
from apps.agency.models import Agency, Client, Note, ClientActivity
from apps.accounts.models import User
from rest_framework.exceptions import NotFound

def get_agency_clients(agency: Agency, search_query: str = None) -> QuerySet[Client]:
    """
    Returns clients for the agency, optionally filtered by a search query.
    """
    queryset = Client.objects.filter(agency=agency).order_by('-created_at')
    if search_query:
        queryset = queryset.filter(
            Q(company__icontains=search_query) |
            Q(contact_person__icontains=search_query) |
            Q(contact_email__icontains=search_query) |
            Q(location__icontains=search_query) |
            Q(industry__icontains=search_query) |
            Q(contact_phone__icontains=search_query)
        )
    return queryset

def get_agency_client_by_id(agency: Agency, client_id: int) -> Client:
    """
    Returns a single client for the agency, or raises NotFound.
    """
    try:
        return Client.objects.get(agency=agency, id=client_id)
    except (Client.DoesNotExist, ValueError):
        raise NotFound("Client not found")

def create_manual_client(agency: Agency, client_data: dict, user=None) -> Client:
    """
    Creates a new client manually for the given agency, and optionally creates an associated note.
    """
    note_content = client_data.pop('note', None)
    
    client = Client.objects.create(
        agency=agency,
        company=client_data.get('company'),
        contact_person=client_data.get('contact_person'),
        contact_email=client_data.get('contact_email'),
        contact_phone=client_data.get('contact_phone'),
        location=client_data.get('location'),
        industry=client_data.get('industry'),
        is_active=client_data.get('is_active', True),
    )
    
    if note_content and note_content.strip() and user:
        Note.objects.create(
            content=note_content.strip(),
            model='client',
            model_id=client.id,
            user=user,
            agency=agency
        )
        
    return client

def update_client(agency: Agency, client: Client, client_data: dict) -> Client:
    """
    Updates a client manually with the given data.
    """
    for field, value in client_data.items():
        setattr(client, field, value)
    client.save()
        
    return client

def get_client_activities(agency: Agency, client_id: int) -> QuerySet[ClientActivity]:
    """
    Returns activities associated with the client for the agency.
    """
    client = get_agency_client_by_id(agency, client_id)
    return ClientActivity.objects.filter(
        agency=agency,
        client=client
    ).select_related('user').order_by('-created_at')

def get_client_notes(agency: Agency, client_id: int) -> QuerySet[Note]:
    """
    Returns notes associated with the client for the agency.
    """
    client = get_agency_client_by_id(agency, client_id)
    return Note.objects.filter(
        agency=agency,
        model='client',
        model_id=client.id
      ).select_related('user').order_by('-created_at')

def add_note_to_client(agency: Agency, user: User, client_id: int, content: str) -> Note:
    """
    Verifies client existence and adds a note to it.
    """
    client = get_agency_client_by_id(agency, client_id)
    note = Note.objects.create(
        content=content,
        model='client',
        model_id=client.id,
        user=user,
        agency=agency
    )
    return note


