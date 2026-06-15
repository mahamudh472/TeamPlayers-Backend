import json
from rest_framework import serializers
from .models import Plan, Subscription

class PlanSerializer(serializers.ModelSerializer):
    feature_list = serializers.SerializerMethodField()

    class Meta:
        model = Plan
        fields = ['id', 'name', 'description', 'price', 'feature_list', 'currency', 'interval', 'created_at', 'updated_at']

    def get_feature_list(self, obj):
        if obj.feature_list:
            try:
                return json.loads(obj.feature_list)
            except json.JSONDecodeError:
                return []
        return []

