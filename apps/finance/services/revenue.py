from decimal import Decimal
from rest_framework.exceptions import ValidationError
from apps.accounts.models import User
from apps.agency.models import Agency, Activity
from apps.agency.services import get_agency_client_by_id
from apps.finance.models import ClientRevenue

def add_client_revenue(agency: Agency, user: User, client_id: int, amount: Decimal) -> ClientRevenue:
    """
    Validates the amount, retrieves the client belonging to the agency,
    records client revenue, and creates a client activity log.
    """
    if amount <= Decimal('0.00'):
        raise ValidationError({"amount": "Revenue amount must be greater than zero."})

    client = get_agency_client_by_id(agency, client_id)

    revenue = ClientRevenue.objects.create(
        client=client,
        agency=agency,
        amount=amount,
        added_by=user
    )

    Activity.objects.create(
        model='client',
        model_id=client.id,
        agency=agency,
        user=user,
        summary=f"Added revenue of {amount}"
    )

    return revenue

