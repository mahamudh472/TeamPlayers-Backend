from django.contrib import admin
from unfold.admin import ModelAdmin, TabularInline
from .models import (
    Agency, AgencyMember, Client, ClientAISummary,
    Candidate, CandidateVersion, CandidateAIAnalysis, LeadGenerationSession, CandidateGatheringSession, Activity,
    Leads, Job, CandidateMeeting, Placement
)

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

@admin.register(Client)
class ClientAdmin(ModelAdmin):
    list_display = ('id', 'company', 'contact_person', 'contact_email', 'contact_phone', 'location', 'industry', 'is_active', 'created_at', 'updated_at')
    search_fields = ('company', 'contact_person', 'contact_email', 'contact_phone', 'location', 'industry')
    ordering = ('-created_at',)

@admin.register(Activity)
class ActivityAdmin(ModelAdmin):
    list_display = ('id', 'model', 'model_id', 'created_at', 'updated_at')
    search_fields = ('model', 'summary')
    ordering = ('-created_at',)

@admin.register(ClientAISummary)
class ClientAISummaryAdmin(ModelAdmin):
    list_display = ('id', 'client', 'summary', 'created_at', 'updated_at')
    search_fields = ('client__company', 'summary')
    ordering = ('-created_at',)

class CandidateVersionInline(TabularInline):
    model = CandidateVersion
    extra = 0
    readonly_fields = ('job', 'name', 'email', 'phone', 'location', 'experience', 'skills', 'current_salary', 'expected_salary', 'resume', 'status', 'ai_extracted_raw_json', 'created_at')
    can_delete = False

@admin.register(Candidate)
class CandidateAdmin(ModelAdmin):
    list_display = ('id', 'name', 'email', 'phone', 'location', 'experience', 'current_salary', 'expected_salary', 'applied_at', 'status')
    search_fields = ('name', 'email', 'location', 'job__title')
    ordering = ('-applied_at',)
    inlines = [CandidateVersionInline]

@admin.register(CandidateVersion)
class CandidateVersionAdmin(ModelAdmin):
    list_display = ('id', 'candidate', 'job', 'name', 'email', 'phone', 'created_at')
    search_fields = ('candidate__name', 'name', 'email', 'phone')
    ordering = ('-created_at',)

@admin.register(CandidateAIAnalysis)
class CandidateAIAnalysisAdmin(ModelAdmin):
    list_display = ('id', 'candidate', 'summary', 'created_at', 'updated_at')
    search_fields = ('candidate__name', 'summary')
    ordering = ('-created_at',)


@admin.register(LeadGenerationSession)
class LeadGenerationSessionAdmin(ModelAdmin):
    list_display = ('id', 'agency', 'user', 'country', 'industry', 'company_size', 'hiring_activity', 'status', 'created_at')
    search_fields = ('agency__name', 'user__email', 'country', 'industry', 'company_size', 'hiring_activity', 'status')
    ordering = ('-created_at',)


@admin.register(CandidateGatheringSession)
class CandidateGatheringSessionAdmin(ModelAdmin):
    list_display = ('id', 'agency', 'user', 'job', 'status', 'created_at')
    search_fields = ('agency__name', 'user__email', 'job__title', 'status')
    ordering = ('-created_at',)



@admin.register(Leads)
class LeadsAdmin(ModelAdmin):
    list_display = ('id', 'company', 'contact_person', 'contact_email', 'priority', 'status', 'created_at')
    list_filter = ('priority', 'status', 'created_at')
    search_fields = ('company', 'contact_person', 'contact_email')
    ordering = ('-created_at',)

@admin.register(Job)
class JobAdmin(ModelAdmin):
    list_display = ('id', 'title', 'client', 'location', 'salary_range', 'job_type', 'status', 'created_at')
    list_filter = ('job_type', 'status', 'created_at')
    search_fields = ('title', 'client__company', 'location')
    ordering = ('-created_at',)

@admin.register(CandidateMeeting)
class CandidateMeetingAdmin(ModelAdmin):
    list_display = ('id', 'candidate', 'meeting_time', 'status', 'created_at')
    list_filter = ('status', 'meeting_time')
    search_fields = ('candidate__name', 'agenda')
    ordering = ('-meeting_time',)

@admin.register(Placement)
class PlacementAdmin(ModelAdmin):
    list_display = ('id', 'candidate', 'job', 'salary', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('candidate__name', 'job__title')
    ordering = ('-created_at',)


