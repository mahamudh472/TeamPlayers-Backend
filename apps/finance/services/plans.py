import json
import os
from django.conf import settings
from apps.finance.models import Plan, Subscription

def seed_subscription_plans(file_path=None) -> dict:
    """
    Seeds subscription plans from a JSON file.
    If the plan already exists (matched by name), it updates the details
    instead of creating duplicates.
    """
    if file_path is None:
        file_path = os.path.join(settings.BASE_DIR, 'assets', 'subscription_plans.json')
    
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Subscription plans file not found at: {file_path}")

    with open(file_path, 'r', encoding='utf-8') as f:
        plans_data = json.load(f)

    results = {
        'created': 0,
        'updated': 0,
    }

    for plan_info in plans_data:
        plan_name = plan_info.get('plan_name')
        if not plan_name:
            continue

        description = plan_info.get('description', '')
        price = plan_info.get('price', 0.0)
        currency = plan_info.get('currency', 'EUR')
        interval = plan_info.get('interval', 'month')
        feature_list = plan_info.get('feature_list', [])

        # Serialize feature list to JSON string for the TextField
        feature_list_str = json.dumps(feature_list)

        plan, created = Plan.objects.update_or_create(
            name=plan_name,
            defaults={
                'description': description,
                'price': price,
                'currency': currency,
                'interval': interval,
                'feature_list': feature_list_str,
            }
        )

        if created:
            results['created'] += 1
        else:
            results['updated'] += 1

    return results


def get_agency_current_subscription(agency_id) -> Subscription:
    """
    Retrieves the active subscription for the given agency.
    """
    return Subscription.objects.filter(agency_id=agency_id, is_active=True).first()
