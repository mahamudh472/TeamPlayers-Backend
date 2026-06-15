from django.db import models

class SiteSettings(models.Model):
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=20, blank=True, null=True)

    address = models.TextField(blank=True, null=True)

    facebook_url = models.URLField(blank=True, null=True)
    twitter_url = models.URLField(blank=True, null=True)
    instagram_url = models.URLField(blank=True, null=True)
    linkedin_url = models.URLField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return "Site Settings"

    @classmethod
    def load(cls):
        # If there are no settings, create a default one
        obj, created = cls.objects.get_or_create(id=1)
        return obj

    class Meta:
        verbose_name = "Site Settings"
        verbose_name_plural = "Site Settings"

class ContactMessage(models.Model):
    full_name = models.CharField(max_length=100)
    email = models.EmailField()
    company_name = models.CharField(max_length=100, blank=True, null=True)
    subject = models.CharField(max_length=200, blank=True, null=True)
    message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Contact Message {self.id}"

    class Meta:
        verbose_name = "Contact Message"
        verbose_name_plural = "Contact Messages"