from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Agency, AgencyMember, Client, ClientActivity, ClientAISummary

@admin.register(Agency)
class AgencyAdmin(ModelAdmin):
    list_display = ('id', 'name', 'created_at', 'updated_at')
    search_fields = ('name',)
    ordering = ('-created_at',)

@admin.register(AgencyMember)
class AgencyMemberAdmin(ModelAdmin):
    list_display = ('id', 'agency', 'user', 'role', 'created_at', 'updated_at')
    search_fields = ('agency__name', 'user__email')
    ordering = ('-created_at',)

@admin.register(Client)
class ClientAdmin(ModelAdmin):
    list_display = ('id', 'company', 'contact_person', 'contact_email', 'contact_phone', 'location', 'industry', 'is_active', 'created_at', 'updated_at')
    search_fields = ('company', 'contact_person', 'contact_email', 'contact_phone', 'location', 'industry')
    ordering = ('-created_at',)

@admin.register(ClientActivity)
class ClientActivityAdmin(ModelAdmin):
    list_display = ('id', 'client', 'created_at', 'updated_at')
    search_fields = ('client__company__name', 'activity')
    ordering = ('-created_at',)

@admin.register(ClientAISummary)
class ClientAISummaryAdmin(ModelAdmin):
    list_display = ('id', 'client', 'summary', 'created_at', 'updated_at')
    search_fields = ('client__company', 'summary')
    ordering = ('-created_at',)

