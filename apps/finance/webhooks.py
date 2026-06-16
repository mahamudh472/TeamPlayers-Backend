import logging
from djstripe.event_handlers import djstripe_receiver
from djstripe.models import Subscription as StripeSubscription
from apps.finance.models import Subscription, Plan
from apps.agency.models import Agency
from django.utils import timezone
import datetime

logger = logging.getLogger(__name__)


def _event_object(event):
    data = getattr(event, "data", {}) or {}
    if isinstance(data, dict):
        return data.get("object") or {}
    return getattr(data, "object", {}) or {}


def _get_value(data, key, default=None):
    if isinstance(data, dict):
        return data.get(key, default)
    if hasattr(data, "get"):
        return data.get(key, default)
    return getattr(data, key, default)


def _datetime_from_timestamp(timestamp):
    if not timestamp:
        return None
    return datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC)


@djstripe_receiver("checkout.session.completed")
def handle_checkout_session_completed(event, **kwargs):
    """
    Called when a Stripe checkout session is successfully completed.
    Links the newly created Stripe subscription with our local Agency and Plan models.
    """
    session = _event_object(event)
    metadata = _get_value(session, "metadata", {}) or {}
    agency_id = _get_value(metadata, "agency_id")
    plan_id = _get_value(metadata, "plan_id")

    if not agency_id or not plan_id:
        logger.warning(
            "Stripe checkout session completed event received, but missing metadata: "
            f"agency_id={agency_id}, plan_id={plan_id}"
        )
        return

    try:
        agency = Agency.objects.get(id=agency_id)
        plan = Plan.objects.get(id=plan_id)
    except (Agency.DoesNotExist, Plan.DoesNotExist) as e:
        logger.error(f"Error finding Agency/Plan from checkout metadata: {str(e)}")
        return

    stripe_sub_id = _get_value(session, "subscription")
    djstripe_sub = None
    if stripe_sub_id:
        djstripe_sub = StripeSubscription.objects.filter(id=stripe_sub_id).first()

    # Deactivate any existing active subscriptions for this agency
    Subscription.objects.filter(agency=agency, is_active=True).update(
        is_active=False,
        updated_at=timezone.now()
    )

    # Set expiration date if available from stripe subscription or session
    expires_at = None
    if djstripe_sub and djstripe_sub.current_period_end:
        expires_at = djstripe_sub.current_period_end
    else:
        expires_at = _datetime_from_timestamp(_get_value(session, "expires_at"))

    plan_snapshot = {
        "id": plan.id,
        "name": plan.name,
        "price": str(plan.price),
        "currency": plan.currency,
        "interval": plan.interval,
        "feature_list": plan.feature_list,
    }

    lookup = {"transaction_id": stripe_sub_id} if stripe_sub_id else {"agency": agency, "plan": plan}
    local_sub, created = Subscription.objects.update_or_create(
        **lookup,
        defaults={
            "agency": agency,
            "plan": plan,
            "plan_snapshot": plan_snapshot,
            "is_active": True,
            "expires_at": expires_at,
            "payment_status": "paid",
            "payment_method": "stripe",
            "stripe_subscription": djstripe_sub,
        },
    )

    logger.info(
        f"Successfully {'created' if created else 'updated'} local Subscription {local_sub.id} "
        f"for agency {agency.id} on plan {plan.name} (Stripe: {stripe_sub_id})"
    )


@djstripe_receiver("customer.subscription.deleted")
def handle_subscription_deleted(event, **kwargs):
    """
    Called when a Stripe subscription is cancelled or deleted.
    Deactivates corresponding local subscriptions.
    """
    stripe_sub = _event_object(event)
    stripe_sub_id = _get_value(stripe_sub, "id")

    if not stripe_sub_id:
        return

    # Update matching active subscriptions to inactive
    updated_count = Subscription.objects.filter(
        transaction_id=stripe_sub_id,
        is_active=True
    ).update(
        is_active=False,
        payment_status="failed",
        updated_at=timezone.now()
    )

    if updated_count > 0:
        logger.info(f"Deactivated {updated_count} local subscriptions linked to cancelled Stripe sub {stripe_sub_id}")


@djstripe_receiver("customer.subscription.updated")
def handle_subscription_updated(event, **kwargs):
    """
    Called when a Stripe subscription is updated (e.g. status changes, period ends, etc.).
    Keeps the local subscription's is_active, payment_status, and expires_at fields synced.
    """
    stripe_sub = _event_object(event)
    stripe_sub_id = _get_value(stripe_sub, "id")
    status = _get_value(stripe_sub, "status")

    if not stripe_sub_id:
        return

    # Stripe active states are 'active' and 'trialing'
    is_active = status in ['active', 'trialing']
    payment_status = "paid" if is_active else "failed" if status in ["unpaid", "incomplete_expired"] else "pending"

    # Fetch corresponding djstripe object to associate if missing
    djstripe_sub = StripeSubscription.objects.filter(id=stripe_sub_id).first()

    expires_at = _datetime_from_timestamp(_get_value(stripe_sub, "current_period_end"))

    # Update matching local subscriptions
    updated_count = Subscription.objects.filter(transaction_id=stripe_sub_id).update(
        is_active=is_active,
        payment_status=payment_status,
        expires_at=expires_at,
        stripe_subscription=djstripe_sub,
        updated_at=timezone.now()
    )

    if updated_count > 0:
        logger.info(
            f"Updated local subscriptions linked to Stripe sub {stripe_sub_id}: "
            f"is_active={is_active}, status={status}, expires_at={expires_at}"
        )
