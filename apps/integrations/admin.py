from django.contrib import admin
from .models import Integration, ZoomToken


@admin.register(Integration)
class IntegrationAdmin(admin.ModelAdmin):
    list_display = ('user', 'agency', 'provider', 'is_connected', 'connected_at')
    list_filter = ('provider', 'is_connected')
    search_fields = ('user__email', 'agency__name')
    readonly_fields = ('id', 'created_at', 'updated_at')


@admin.register(ZoomToken)
class ZoomTokenAdmin(admin.ModelAdmin):
    list_display = ('integration', 'token_type', 'expires_at')
    readonly_fields = ('created_at', 'updated_at')
