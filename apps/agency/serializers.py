from rest_framework import serializers
from apps.agency.models import AgencyMember

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
