from apps.main.models import ContactMessage

def create_contact_message(data: dict) -> ContactMessage:
    """
    Creates a new contact message in the database and returns the instance.
    """
    return ContactMessage.objects.create(**data)
