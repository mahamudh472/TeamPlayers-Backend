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


def get_verified_agency(user, agency_id) -> Agency:
    """
    Validates that the agency exists and the user is an active, accepted member of it.
    Raises PermissionDenied or NotFound if invalid.
    """
    from rest_framework.exceptions import PermissionDenied, NotFound

    if not agency_id:
        raise PermissionDenied("X-Agency-ID header is required")
    try:
        agency = Agency.objects.get(id=agency_id)
    except (Agency.DoesNotExist, ValueError):
        raise NotFound("Agency not found")
        
    is_member = AgencyMember.objects.filter(
        agency=agency,
        user=user,
        invitation_status='accepted',
        is_active=True
    ).exists()
    
    if not is_member:
        raise PermissionDenied("You do not have permission to access this agency")
        
    return agency


