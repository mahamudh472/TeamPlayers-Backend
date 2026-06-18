from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import User
from apps.agency.models import Leads, Client
from apps.agency.services import create_agency_for_user

@receiver(post_save, sender=User)
def handle_user_created(sender, instance, created, **kwargs):
    """
    Signal handler that creates a default Agency and associates the user as its owner
    whenever a new User is created.
    """
    if created:
        agency_name = getattr(instance, 'agency_name', None)
        create_agency_for_user(instance, agency_name=agency_name)

@receiver(post_save, sender=Leads)
def handle_lead_status_changed(sender, instance, **kwargs):
    """
    Signal handler that creates a Client object when a Lead's status is changed to 'converted'.
    """
    if instance.status == 'converted':
        # Create a Client if it doesn't already exist for this Lead
        Client.objects.get_or_create(
            lead=instance,
            defaults={
                'agency': instance.agency,
                'company': instance.company,
                'contact_person': instance.contact_person,
                'contact_email': instance.contact_email,
                'contact_phone': instance.contact_phone,
                'location': instance.location,
                'industry': instance.industry,
            }
        )
