from apps.agency.models import Agency, AgencyMember

def create_agency_for_user(user) -> Agency:
    """
    Creates a default agency for a user and registers the user as the owner.
    """
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
