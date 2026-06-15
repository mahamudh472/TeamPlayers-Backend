from rest_framework import serializers
from .models import ContactMessage

class ContactMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ContactMessage
        fields = [
            'id',
            'full_name',
            'email',
            'company_name',
            'subject',
            'message',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']
