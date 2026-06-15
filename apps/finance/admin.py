from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Plan, Subscription

@admin.register(Plan)
class PlanAdmin(ModelAdmin):
    list_display = ('name', 'price', 'currency', 'interval')
    list_filter = ('currency', 'interval')
    search_fields = ('name', 'description')
    ordering = ('name',)

@admin.register(Subscription)
class SubscriptionAdmin(ModelAdmin):
    list_display = ('agency', 'plan', 'is_active', 'created_at', 'updated_at')
    list_filter = ('is_active', 'created_at', 'updated_at')
    search_fields = ('agency__name', 'plan__name')
    ordering = ('created_at',)

    def get_queryset(self, request):
        return super().get_queryset(request).select_related('agency').select_related('plan')
