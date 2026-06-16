import datetime
from types import SimpleNamespace

from django.test import TestCase

from apps.agency.models import Agency
from apps.finance.models import Plan, Subscription
from apps.finance.webhooks import (
    handle_checkout_session_completed,
    handle_subscription_deleted,
    handle_subscription_updated,
)


class StripeWebhookTests(TestCase):
    def setUp(self):
        self.agency = Agency.objects.create(name="Test Agency")
        self.plan = Plan.objects.create(
            name="Starter",
            price="49.99",
            currency="USD",
            interval="month",
            feature_list='["Feature A"]',
        )

    def _event(self, obj):
        return SimpleNamespace(data={"object": obj})

    def test_checkout_session_completed_creates_local_subscription_from_dict_payload(self):
        expires_at = int(datetime.datetime(2026, 7, 16, tzinfo=datetime.UTC).timestamp())
        event = self._event({
            "metadata": {
                "agency_id": str(self.agency.id),
                "plan_id": str(self.plan.id),
            },
            "subscription": "sub_test_123",
            "expires_at": expires_at,
        })

        handle_checkout_session_completed(event)

        subscription = Subscription.objects.get(transaction_id="sub_test_123")
        self.assertEqual(subscription.agency, self.agency)
        self.assertEqual(subscription.plan, self.plan)
        self.assertTrue(subscription.is_active)
        self.assertEqual(subscription.payment_status, "paid")
        self.assertEqual(subscription.payment_method, "stripe")

    def test_checkout_session_completed_is_idempotent_for_retried_event(self):
        event = self._event({
            "metadata": {
                "agency_id": str(self.agency.id),
                "plan_id": str(self.plan.id),
            },
            "subscription": "sub_test_123",
        })

        handle_checkout_session_completed(event)
        handle_checkout_session_completed(event)

        self.assertEqual(Subscription.objects.filter(transaction_id="sub_test_123").count(), 1)

    def test_subscription_updated_accepts_dict_payload(self):
        Subscription.objects.create(
            agency=self.agency,
            plan=self.plan,
            transaction_id="sub_test_123",
            payment_status="pending",
        )
        period_end = int(datetime.datetime(2026, 8, 16, tzinfo=datetime.UTC).timestamp())
        event = self._event({
            "id": "sub_test_123",
            "status": "active",
            "current_period_end": period_end,
        })

        handle_subscription_updated(event)

        subscription = Subscription.objects.get(transaction_id="sub_test_123")
        self.assertTrue(subscription.is_active)
        self.assertEqual(subscription.payment_status, "paid")
        self.assertIsNotNone(subscription.expires_at)

    def test_subscription_deleted_accepts_dict_payload(self):
        Subscription.objects.create(
            agency=self.agency,
            plan=self.plan,
            transaction_id="sub_test_123",
            is_active=True,
            payment_status="paid",
        )
        event = self._event({"id": "sub_test_123"})

        handle_subscription_deleted(event)

        subscription = Subscription.objects.get(transaction_id="sub_test_123")
        self.assertFalse(subscription.is_active)
        self.assertEqual(subscription.payment_status, "failed")
