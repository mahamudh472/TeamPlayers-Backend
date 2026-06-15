from apps.agency.models import Agency
from django.db import models

class Plan(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    feature_list = models.TextField(blank=True, null=True)
    currency = models.CharField(max_length=3, choices=[('USD', 'USD'), ('EUR', 'EUR'), ('GBP', 'GBP')], default='USD')
    interval = models.CharField(max_length=10, choices=[('month', 'Month'), ('year', 'Year')], default='month')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Plan"
        verbose_name_plural = "Plans"

class Subscription(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='subscriptions')
    plan = models.ForeignKey(Plan, on_delete=models.CASCADE, related_name='subscriptions')
    plan_snapshot = models.JSONField(default=dict)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(blank=True, null=True)
    payment_status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed')], default='pending')
    payment_method = models.CharField(max_length=20, choices=[('stripe', 'Stripe'), ('paypal', 'Paypal')], default='stripe')
    transaction_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Subscription {self.id}"

    class Meta:
        verbose_name = "Subscription"
        verbose_name_plural = "Subscriptions"