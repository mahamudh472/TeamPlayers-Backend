import uuid
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

    # Extended fields from n8n
    website = models.URLField(max_length=255, blank=True, null=True)
    company_domain = models.CharField(max_length=255, blank=True, null=True)
    linkedin = models.URLField(max_length=255, blank=True, null=True)
    company_size = models.CharField(max_length=100, blank=True, null=True)
    employee_count = models.IntegerField(blank=True, null=True)
    hiring_activity = models.CharField(max_length=255, blank=True, null=True)
    job_title = models.CharField(max_length=255, blank=True, null=True)
    job_type = models.CharField(max_length=100, blank=True, null=True)
    job_level = models.CharField(max_length=100, blank=True, null=True)
    is_remote = models.BooleanField(null=True, blank=True)
    job_url = models.URLField(max_length=500, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    detected_at = models.DateTimeField(blank=True, null=True)
    domain_source = models.CharField(max_length=100, blank=True, null=True)
    enriched_at = models.DateTimeField(blank=True, null=True)

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
        ('client', 'Client'), 
        ('meeting', 'Meeting'),
        ('candidate', 'Candidate')
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


class Activity(models.Model):
    summary = models.TextField(blank=True, null=True)
    model = models.CharField(max_length=20, choices=[
        ('client', 'Client'),
        ('candidate', 'Candidate'),
        ('lead', 'Lead'),
        ('job', 'Job'),
        ('member', 'Member'),
        ('placement', 'Placement'),
        ('agency', 'Agency'),
    ])
    model_id = models.PositiveIntegerField(null=True, blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='activities')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='activities')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Activity"
        verbose_name_plural = "Activities"

    def __str__(self):
        return self.summary if self.summary else f"Activity {self.id}"


class Client(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='clients')
    lead = models.ForeignKey(Leads, on_delete=models.CASCADE, related_name='clients', blank=True, null=True)
    
    company = models.CharField(max_length=100)
    contact_person = models.CharField(max_length=100, blank=True, null=True)
    contact_email = models.EmailField(blank=True, null=True)
    contact_phone = models.CharField(max_length=15, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def __str__(self):
        if self.lead and self.lead.company:
            return self.lead.company
        return self.company if self.company else f"Client {self.id}"

class ClientAISummary(models.Model):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='ai_summaries')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='client_ai_summaries')
    
    summary = models.TextField(blank=True, null=True)
    collabration_strength = models.JSONField(default=list, blank=True, null=True)
    risks = models.JSONField(default=list, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Client AI Summary"
        verbose_name_plural = "Client AI Summaries"

    def __str__(self):
        return f"Client AI Summary {self.id} for {self.client.company}"

class Job(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='jobs')
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name='jobs')
    
    title = models.CharField(max_length=100)
    description = models.TextField()
    location = models.CharField(max_length=100, blank=True, null=True)
    salary_range = models.CharField(max_length=50, blank=True, null=True)
    experince_required = models.IntegerField(default=0)
    skills = models.JSONField(default=list, blank=True, null=True)  
    
    job_type = models.CharField(max_length=20, choices=[
        ('full-time', 'Full Time'), 
        ('part-time', 'Part Time'),
        ('hybrid', 'Hybrid'),
        ('remote', 'Remote'),
        ('contract', 'Contract')], default='full-time')
    
    status = models.CharField(max_length=20, choices=[
        ('open', 'Open'), 
        ('closed', 'Closed'), 
        ('filled', 'Filled')], default='open')
    description_file = models.FileField(upload_to='job_descriptions', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Job"
        verbose_name_plural = "Jobs"

    def __str__(self):
        return self.title if self.title else f"Job {self.id}"    

class Candidate(models.Model):
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='candidates')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='candidates')

    ai_extracted_raw_json = models.JSONField(blank=True, null=True)
    
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=15, blank=True, null=True)
    location = models.CharField(max_length=100, blank=True, null=True)
    experience = models.IntegerField(default=0)
    skills = models.JSONField(default=list, blank=True, null=True)
    current_salary = models.CharField(max_length=50, blank=True, null=True)
    expected_salary = models.CharField(max_length=50, blank=True, null=True)
    resume = models.FileField(upload_to='candidates/resumes', blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=[
        ('new', 'New'),
        ('shortlisted', 'Shortlisted'),
        ('interviewing', 'Interviewing'),
        ('offered', 'Offered'),
        ('accepted', 'Accepted'),
        ('rejected', 'Rejected')], default='new')
    
    applied_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Candidate"
        verbose_name_plural = "Candidates"

    def __str__(self):
        return self.name if self.name else f"Candidate {self.id}"

class CandidateAIAnalysis(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='ai_analysis')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='candidate_ai_analysis')
    
    summary = models.TextField(blank=True, null=True)

    key_strength = models.JSONField(default=list, blank=True, null=True)
    potential_concerns = models.JSONField(default=list, blank=True, null=True)

    # AI match breackdown
    skills_match = models.FloatField(default=0) 
    experience_match = models.FloatField(default=0)
    salary_match = models.FloatField(default=0)
    location_match = models.FloatField(default=0)
    overall_match_percentage = models.FloatField(default=0) 
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Candidate AI Analysis"
        verbose_name_plural = "Candidate AI Analysis"

    def __str__(self):
        return f"Candidate AI Analysis {self.id} for {self.candidate.name}"



class CandidateMeeting(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='meetings')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='candidate_meetings')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='candidate_meetings')
    
    meeting_time = models.DateTimeField(blank=True, null=True)
    agenda = models.TextField(blank=True, null=True)
    
    summary = models.TextField(blank=True, null=True)
    meeting_link = models.URLField(blank=True, null=True)
    
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'), 
        ('scheduled', 'Scheduled'), 
        ('completed', 'Completed'), 
        ('cancelled', 'Cancelled')], default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Candidate Meeting"
        verbose_name_plural = "Candidate Meetings"

    def __str__(self):
        return self.summary if self.summary else f"Candidate Meeting {self.id}"

class Placement(models.Model):
    candidate = models.ForeignKey(Candidate, on_delete=models.CASCADE, related_name='placements')
    job = models.ForeignKey(Job, on_delete=models.CASCADE, related_name='placements')
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='placements')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='placements')
    salary = models.DecimalField(max_digits=10, decimal_places=2, blank=True, null=True)
    notice_period = models.IntegerField(blank=True, null=True)
    status = models.CharField(max_length=20, choices=[
        ('placed', 'Placed'),
        ('not_placed', 'Not Placed')], default='placed')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Placement"
        verbose_name_plural = "Placements"

    def __str__(self):
        return f"Placement {self.id} for {self.candidate.name}"


class LeadGenerationSession(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    agency = models.ForeignKey(Agency, on_delete=models.CASCADE, related_name='lead_generation_sessions')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='lead_generation_sessions')

    country = models.CharField(max_length=100, blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    company_size = models.CharField(max_length=100, blank=True, null=True)
    hiring_activity = models.CharField(max_length=100, blank=True, null=True)

    status = models.CharField(max_length=20, choices=[
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed')
    ], default='pending')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lead_generation_sessions'
        verbose_name = 'Lead Generation Session'
        verbose_name_plural = 'Lead Generation Sessions'
        ordering = ['-created_at']

    def __str__(self):
        return f"Session {self.id} ({self.status})"