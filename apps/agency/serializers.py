from rest_framework import serializers
from apps.agency.models import AgencyMember, Leads, Note, Client, ClientAISummary, Job, ClientActivity
from apps.accounts.models import User

class UserAgencySerializer(serializers.ModelSerializer):
    agency_id = serializers.IntegerField(source='agency.id', read_only=True)
    agency_name = serializers.CharField(source='agency.name', read_only=True)

    class Meta:
        model = AgencyMember
        fields = [
            'agency_id',
            'agency_name',
            'role'
        ]
        read_only_fields = fields


class UserMinSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'email', 'full_name']


class LeadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Leads
        fields = [
            'id',
            'company',
            'contact_person',
            'contact_email',
            'contact_phone',
            'location',
            'industry',
            'source',
            'priority',
            'status',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class NoteSerializer(serializers.ModelSerializer):
    user = UserMinSerializer(read_only=True)
    
    class Meta:
        model = Note
        fields = [
            'id',
            'content',
            'model',
            'model_id',
            'user',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'model', 'model_id', 'user', 'created_at', 'updated_at']


class LeadDetailSerializer(serializers.ModelSerializer):
    notes = serializers.SerializerMethodField()
    
    class Meta:
        model = Leads
        fields = [
            'id',
            'company',
            'contact_person',
            'contact_email',
            'contact_phone',
            'location',
            'industry',
            'source',
            'priority',
            'status',
            'created_at',
            'updated_at',
            'notes'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'notes']

    def get_notes(self, obj):
        from apps.agency.services.leads import get_lead_notes
        notes = get_lead_notes(obj.agency, obj.id)
        return NoteSerializer(notes, many=True).data


class ClientSerializer(serializers.ModelSerializer):
    jobs = serializers.SerializerMethodField()
    placements = serializers.SerializerMethodField()
    revenue = serializers.SerializerMethodField()
    note = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Client
        fields = [
            'id',
            'lead',
            'company',
            'contact_person',
            'contact_email',
            'contact_phone',
            'location',
            'industry',
            'is_active',
            'jobs',
            'placements',
            'revenue',
            'note',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'lead', 'created_at', 'updated_at']

    def get_jobs(self, obj):
        return obj.jobs.count()

    def get_placements(self, obj):
        # TODO: Make this dynamic once we have data tracking
        return 0

    def get_revenue(self, obj):
        # TODO: Make this dynamic once we have data tracking
        return 15000.00

    def validate(self, attrs):
        if self.instance and 'note' in attrs:
            raise serializers.ValidationError({"note": "The note field is not allowed on client update."})
        return attrs


class ClientAISummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = ClientAISummary
        fields = ['id', 'summary', 'collabration_strength', 'risks', 'created_at', 'updated_at']


class ClientActivitySerializer(serializers.ModelSerializer):
    user = UserMinSerializer(read_only=True)

    class Meta:
        model = ClientActivity
        fields = [
            'id',
            'client',
            'user',
            'summary',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'client', 'user', 'created_at', 'updated_at']


class ClientDetailSerializer(ClientSerializer):
    success_rate = serializers.SerializerMethodField()
    last_ai_summary = serializers.SerializerMethodField()
    client_health = serializers.SerializerMethodField()
    hiring_success_rate = serializers.SerializerMethodField()
    recommended_actions = serializers.SerializerMethodField()

    class Meta(ClientSerializer.Meta):
        fields = ClientSerializer.Meta.fields + [
            'success_rate',
            'last_ai_summary',
            'client_health',
            'hiring_success_rate',
            'recommended_actions'
        ]

    def get_success_rate(self, obj):
        # TODO: Make this dynamic once we have data tracking
        return 92.5

    def get_last_ai_summary(self, obj):
        last_summary = obj.ai_summaries.order_by('-created_at').first()
        if last_summary:
            return ClientAISummarySerializer(last_summary).data
        return None

    def get_client_health(self, obj):
        # TODO: Make this dynamic once we have data tracking
        return "healthy"

    def get_hiring_success_rate(self, obj):
        # TODO: Make this dynamic once we have data tracking
        return 88.0

    def get_recommended_actions(self, obj):
        # TODO: Make this dynamic once we have data tracking
        return [
            "Schedule quarterly review meeting",
            "Follow up on pending candidate interviews",
            "Send renewal proposal for the technical consulting contract"
        ]


class JobSerializer(serializers.ModelSerializer):
    client_name = serializers.CharField(source='client.company', read_only=True)
    applicants = serializers.SerializerMethodField()
    shortlisted = serializers.SerializerMethodField()
    interviewed = serializers.SerializerMethodField()

    class Meta:
        model = Job
        fields = [
            'id',
            'client',
            'client_name',
            'title',
            'description',
            'location',
            'salary_range',
            'experince_required',
            'skills',
            'job_type',
            'status',
            'description_file',
            'applicants',
            'shortlisted',
            'interviewed',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'client_name', 'created_at', 'updated_at']

    def get_applicants(self, obj):
        return 12

    def get_shortlisted(self, obj):
        return 4

    def get_interviewed(self, obj):
        return 2

    def validate(self, attrs):
        agency = self.context.get('agency')
        client = attrs.get('client')
        if agency and client and client.agency != agency:
            raise serializers.ValidationError({"client": "Client does not belong to this agency."})
        return attrs
