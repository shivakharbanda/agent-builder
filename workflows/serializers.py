from rest_framework import serializers
from .models import DataSource, Workflow, WorkflowProperties, WorkflowExecution, WorkflowNode, PlaceholderMapping, OutputNode


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
            'id', 'node_type', 'position', 'visual_position', 'configuration', 'agent', 'agent_name',
            'data_source', 'data_source_name', 'placeholder_mappings',
            'created_at', 'updated_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'agent_name', 'data_source_name']


class OutputNodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutputNode
        fields = ['id', 'destination_table', 'configuration', 'created_at', 'updated_at', 'created_by', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']


class WorkflowPropertiesSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowProperties
        fields = [
            'id', 'watermark_start_date', 'watermark_end_date', 'schedule',
            'timeout', 'retry_count', 'notification_email', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class WorkflowExecutionSerializer(serializers.ModelSerializer):
    class Meta:
        model = WorkflowExecution
        fields = [
            'id', 'status', 'started_at', 'completed_at', 'execution_log',
            'error_message', 'triggered_by', 'created_at', 'updated_at', 'created_by'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class WorkflowSerializer(serializers.ModelSerializer):
    nodes = WorkflowNodeSerializer(many=True, read_only=True)
    output_nodes = OutputNodeSerializer(many=True, read_only=True)
    properties = WorkflowPropertiesSerializer(read_only=True)
    current_execution = serializers.SerializerMethodField()
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'project', 'project_name', 'configuration',
            'properties', 'current_execution', 'nodes', 'output_nodes',
            'created_at', 'updated_at', 'created_by', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'project_name']

    def get_current_execution(self, obj):
        latest_execution = obj.executions.first()  # Due to ordering by -created_at
        if latest_execution:
            return {
                'id': latest_execution.id,
                'status': latest_execution.status,
                'created_at': latest_execution.created_at
            }
        return None

    def create(self, validated_data):
        # created_by should be passed explicitly from the view
        if 'created_by' not in validated_data:
            # Fallback to context if available, but don't fail if missing
            request = self.context.get('request')
            if request and hasattr(request, 'user'):
                validated_data['created_by'] = request.user

        workflow = super().create(validated_data)

        # Create default properties
        WorkflowProperties.objects.create(
            workflow=workflow,
            created_by=validated_data['created_by']
        )

        # Create initial execution record
        WorkflowExecution.objects.create(
            workflow=workflow,
            status='draft',
            created_by=validated_data['created_by']
        )

        return workflow


class WorkflowListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for workflow lists"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    nodes_count = serializers.SerializerMethodField()
    current_status = serializers.SerializerMethodField()

    class Meta:
        model = Workflow
        fields = [
            'id', 'name', 'description', 'project_name', 'current_status',
            'nodes_count', 'created_at', 'is_active'
        ]

    def get_nodes_count(self, obj):
        return obj.nodes.filter(is_active=True).count()

    def get_current_status(self, obj):
        latest_execution = obj.executions.first()
        return latest_execution.status if latest_execution else 'draft'