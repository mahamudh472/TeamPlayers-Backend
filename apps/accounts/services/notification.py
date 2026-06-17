from apps.accounts.models import NotificationSettings

def get_or_create_notification_settings(user) -> NotificationSettings:
    """
    Retrieves the notification settings for the user.
    If they do not exist, they are created.
    """
    settings, created = NotificationSettings.objects.get_or_create(user=user)
    return settings

def update_notification_settings(user, data: dict) -> NotificationSettings:
    """
    Updates the notification settings for the user.
    """
    settings = get_or_create_notification_settings(user)
    fields = ['new_application', 'interview_reminder', 'new_lead', 'weekly_report', 'marketing_email']
    for field in fields:
        if field in data:
            setattr(settings, field, data[field])
    settings.save()
    return settings
