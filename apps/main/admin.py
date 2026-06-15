from django.contrib import admin
from unfold.admin import ModelAdmin
from .models import ContactMessage, SiteSettings

@admin.register(ContactMessage)
class ContactMessageAdmin(ModelAdmin):
    list_display = ('id', 'full_name', 'email', 'company_name', 'subject', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('full_name', 'email', 'company_name', 'subject', 'message')
    ordering = ('-created_at',)

@admin.register(SiteSettings)
class SiteSettingsAdmin(ModelAdmin):
    list_display = ('contact_email', 'contact_phone', 'address')

