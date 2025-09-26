from rest_framework import serializers
from .models import Project


class ProjectSerializer(serializers.ModelSerializer):
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'created_at', 'updated_at', 'created_by', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class ProjectListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for project lists"""
    agents_count = serializers.SerializerMethodField()
    workflows_count = serializers.SerializerMethodField()

    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'created_at', 'is_active', 'agents_count', 'workflows_count']

    def get_agents_count(self, obj):
        return obj.agents.filter(is_active=True).count()

    def get_workflows_count(self, obj):
        return obj.workflows.filter(is_active=True).count()