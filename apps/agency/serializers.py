from rest_framework import serializers
from apps.agency.models import AgencyMember, Leads, Note
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

