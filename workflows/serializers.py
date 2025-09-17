from rest_framework import serializers
from .models import DataSource, Workflow, WorkflowNode, PlaceholderMapping, OutputNode


class DataSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = DataSource
        fields = [
            'id', 'name', 'source_type', 'connection_config', 'load_mode',
            'watermark_start_date', 'watermark_end_date', 'table_name',
            'created_at', 'updated_at', 'created_by', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class PlaceholderMappingSerializer(serializers.ModelSerializer):
    class Meta:
        model = PlaceholderMapping
        fields = ['id', 'placeholder_name', 'data_column', 'transformation', 'created_at', 'is_active']
        read_only_fields = ['id', 'created_at']


class WorkflowNodeSerializer(serializers.ModelSerializer):
    placeholder_mappings = PlaceholderMappingSerializer(many=True, read_only=True)
    agent_name = serializers.CharField(source='agent.name', read_only=True)
    data_source_name = serializers.CharField(source='data_source.name', read_only=True)

    class Meta:
        model = WorkflowNode
        fields = [
            'id', 'node_type', 'position', 'configuration', 'agent', 'agent_name',
            'data_source', 'data_source_name', 'placeholder_mappings',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'agent_name', 'data_source_name']


class OutputNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutputNode
        fields = ['id', 'destination_table', 'configuration', 'created_at', 'updated_at', 'created_by', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class WorkflowSerializer(serializers.ModelSerializer):
    nodes = WorkflowNodeSerializer(many=True, read_only=True)
    output_nodes = OutputNodeSerializer(many=True, read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'project', 'project_name', 'configuration',
            'status', 'nodes', 'output_nodes', 'created_at', 'updated_at', 'created_by', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'project_name']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class WorkflowListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for workflow lists"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    nodes_count = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'project_name', 'status',
            'nodes_count', 'created_at', 'is_active'
        ]

    def get_nodes_count(self, obj):
        return obj.nodes.filter(is_active=True).count()