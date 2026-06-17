from email.policy import default
from django.db import models
from apps.accounts.models import User

class Agency(models.Model):
    logo = models.ImageField(upload_to='agencies/logos/', blank=True, null=True)
    name = models.CharField(max_length=100)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name if self.name else f"Agency {self.id}"

class AgencyMember(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='members')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='agencies')

    invitation_date = models.DateTimeField(auto_now_add=True)
    invitation_status = models.CharField(max_length=20, choices=[('pending', 'Pending'), ('accepted', 'Accepted'), ('rejected', 'Rejected')])
    role = models.CharField(max_length=20, choices=[('owner', 'Owner'), ('admin', 'Admin'), ('recruiter', 'Recruiter')], default='recruiter')
    
    is_active = models.BooleanField(default=True) 

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('agency', 'user')
        verbose_name = "Agency Member"
        verbose_name_plural = "Agency Members"
        
    def __str__(self):
        return f"{self.user.email} in {self.agency.name} as {self.role}"


class Leads(models.Model):
    company = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=15, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    source = models.CharField(max_length=100, blank=True, null=True)
    priority = models.CharField(max_length=20, choices=[
        ('low', 'Low'), 
        ('medium', 'Medium'), 
        ('high', 'High')
    ], default='low')
    status = models.CharField(max_length=20, choices=[
        ('new', 'New'), 
        ('contacted', 'Contacted'),
        ('meeting', 'Meeting'),
        ('converted', 'Converted'), 
        ('lost', 'Lost')
    ], default='new')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='leads')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Lead"
        verbose_name_plural = "Leads"

    def __str__(self):
        return self.company if self.company else f"Lead {self.id}"

class Note(models.Model):
    content = models.TextField()
    model = models.CharField(max_length=20, choices=[
        ('lead', 'Lead'), 
        ('task', 'Task'), 
        ('event', 'Event')
        ],
    )
    model_id = models.PositiveIntegerField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notes')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='notes')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Note"
        verbose_name_plural = "Notes"

    def __str__(self):
        return self.content if self.content else f"Note {self.id}"


