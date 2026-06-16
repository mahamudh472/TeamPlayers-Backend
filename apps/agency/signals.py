from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.accounts.models import User
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
