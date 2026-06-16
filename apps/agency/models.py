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
