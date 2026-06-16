import stripe
from django.conf import settings
from djstripe.models import Customer
from apps.finance.models import Plan

def get_or_create_stripe_customer(user) -> Customer:
    """
    Retrieves or creates a dj-stripe Customer for the user.
    """
    customer, _ = Customer.get_or_create(subscriber=user)
    return customer

def ensure_stripe_price_and_product(plan: Plan) -> Plan:
    """
    Lazily creates a corresponding Product and Price in Stripe if they don't exist.
    """
    if not plan.stripe_price_id or not plan.stripe_product_id:
        stripe.api_key = settings.STRIPE_SECRET_KEY

        # Check for existing active Product in Stripe by name to avoid duplicates
        product_id = None
        try:
            products = stripe.Product.list(active=True)
            for prod in products.data:
                if prod.name == plan.name:
                    product_id = prod.id
                    break
        except Exception:
            pass

        if not product_id:
            stripe_prod = stripe.Product.create(
                name=plan.name,
                description=plan.description or ""
            )
            product_id = stripe_prod.id

        # Create Price on Stripe
        price_cents = int(plan.price * 100)
        stripe_price = stripe.Price.create(
            unit_amount=price_cents,
            currency=plan.currency.lower(),
            recurring={"interval": plan.interval},
            product=product_id,
        )

        plan.stripe_product_id = product_id
        plan.stripe_price_id = stripe_price.id
        plan.save()

    return plan

def create_checkout_session(user, agency, plan: Plan, success_url: str, cancel_url: str) -> dict:
    """
    Creates a Stripe Checkout Session for a plan subscription.
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # Ensure Stripe Product and Price exist
    plan = ensure_stripe_price_and_product(plan)

    # Retrieve or create customer
    customer = get_or_create_stripe_customer(user)

    # Create session
    session = stripe.checkout.Session.create(
        customer=customer.id,
        payment_method_types=['card'],
        line_items=[{
            'price': plan.stripe_price_id,
            'quantity': 1,
        }],
        mode='subscription',
        success_url=success_url,
        cancel_url=cancel_url,
        metadata={
            'agency_id': str(agency.id),
            'user_id': str(user.id),
            'plan_id': str(plan.id),
        },
        subscription_data={
            'metadata': {
                'agency_id': str(agency.id),
                'user_id': str(user.id),
                'plan_id': str(plan.id),
            }
        }
    )

    return {
        "checkout_url": session.url,
        "session_id": session.id
    }

def create_billing_portal_session(user, return_url: str) -> str:
    """
    Creates a Stripe Billing Portal session for the user.
    """
    stripe.api_key = settings.STRIPE_SECRET_KEY

    customer = Customer.objects.filter(subscriber=user).first()
    if not customer:
        raise ValueError("Stripe customer not found. You must purchase a subscription first.")

    session = stripe.billing_portal.Session.create(
        customer=customer.id,
        return_url=return_url,
    )
    return session.url
