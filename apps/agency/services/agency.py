from django.db.models import QuerySet
from apps.agency.models import Agency, AgencyMember

def create_agency_for_user(user, agency_name=None) -> Agency:
    """
    Creates a default agency for a user and registers the user as the owner.
    """
    if not agency_name:
        if user.full_name:
            agency_name = f"{user.full_name}'s Agency"
        else:
            agency_name = f"{user.email.split('@')[0]}'s Agency"
        
    agency = Agency.objects.create(
        name=agency_name,
    )
    
    AgencyMember.objects.create(
        agency=agency,
        user=user,
        role='owner',
        invitation_status='accepted',
        is_active=True
    )
    
    return agency

def get_user_agencies(user) -> QuerySet[AgencyMember]:
    """
    Returns the active and accepted agency memberships for the given user.
    """
    return AgencyMember.objects.filter(
        user=user,
        is_active=True,
        invitation_status='accepted'
    ).select_related('agency')

