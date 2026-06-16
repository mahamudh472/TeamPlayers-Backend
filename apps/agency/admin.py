from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import Agency, AgencyMember

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

