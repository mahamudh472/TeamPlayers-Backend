from apps.integrations.models import Integration

def get_available_integrations(user, agency_id) -> list[dict]:
    """
    Returns all available integrations and their connection status
    for the specified user and agency.
    """
    existing_integrations = {
        integration.provider: integration
        for integration in Integration.objects.filter(user=user, agency_id=agency_id)
    }

    available = []
    for provider_code, provider_name in Integration.PROVIDER_CHOICES:
        integration = existing_integrations.get(provider_code)
        if integration:
            available.append({
                'id': integration.id,
                'provider': provider_code,
                'name': provider_name,
                'is_connected': integration.is_connected,
                'connected_at': integration.connected_at,
                'metadata': integration.metadata,
                'created_at': integration.created_at,
                'updated_at': integration.updated_at,
            })
        else:
            available.append({
                'id': None,
                'provider': provider_code,
                'name': provider_name,
                'is_connected': False,
                'connected_at': None,
                'metadata': {},
                'created_at': None,
                'updated_at': None,
            })
    return available
