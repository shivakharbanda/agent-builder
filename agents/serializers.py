from rest_framework import serializers
from django.db import transaction
from .models import Agent, Prompt, Tool, AgentTool


class PromptSerializer(serializers.ModelSerializer):
    class Meta:
        model = Prompt
        fields = ['id', 'prompt_type', 'content', 'placeholders', 'created_at', 'updated_at', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at']


class ToolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tool
        fields = ['id', 'name', 'description', 'tool_type', 'configuration', 'created_at', 'updated_at', 'created_by', 'is_active']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class AgentToolSerializer(serializers.ModelSerializer):
    tool_name = serializers.CharField(source='tool.name', read_only=True)
    tool_type = serializers.CharField(source='tool.tool_type', read_only=True)

    class Meta:
        model = AgentTool
        fields = ['id', 'tool', 'tool_name', 'tool_type', 'configuration', 'created_at', 'is_active']
        read_only_fields = ['id', 'created_at', 'tool_name', 'tool_type']


class AgentSerializer(serializers.ModelSerializer):
    prompts = PromptSerializer(many=True, read_only=True)
    agent_tools = AgentToolSerializer(many=True, read_only=True)
    project_name = serializers.CharField(source='project.name', read_only=True)

    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'return_type', 'schema_definition',
            'project', 'project_name', 'prompts', 'agent_tools',
            'created_at', 'updated_at', 'created_by', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'project_name', 'project']

    def validate(self, data):
        # Validate that structured agents have a schema definition
        if data.get('return_type') == 'structured' and not data.get('schema_definition'):
            raise serializers.ValidationError({
                'schema_definition': 'Schema definition is required for structured return type.'
            })
        return data

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class AgentListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for agent lists"""
    project_name = serializers.CharField(source='project.name', read_only=True)
    prompts_count = serializers.SerializerMethodField()
    tools_count = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'return_type', 'project_name',
            'prompts_count', 'tools_count', 'created_at', 'is_active'
        ]

    def get_prompts_count(self, obj):
        return obj.prompts.filter(is_active=True).count()

    def get_tools_count(self, obj):
        return obj.agent_tools.filter(is_active=True).count()


class PromptCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating prompts within agent creation"""
    class Meta:
        model = Prompt
        fields = ['prompt_type', 'content', 'placeholders']


class AgentCompleteCreateSerializer(serializers.ModelSerializer):
    """Serializer for complete agent creation with prompts and tools"""
    prompts = PromptCreateSerializer(many=True, required=False)
    tool_ids = serializers.ListField(
        child=serializers.IntegerField(),
        required=False,
        write_only=True
    )

    class Meta:
        model = Agent
        fields = [
            'name', 'description', 'return_type', 'schema_definition',
            'project', 'prompts', 'tool_ids'
        ]

    def validate_tool_ids(self, value):
        """Validate that all tool IDs exist"""
        if value:
            existing_tools = Tool.objects.filter(id__in=value, is_active=True)
            if len(existing_tools) != len(value):
                raise serializers.ValidationError("One or more tool IDs are invalid")
        return value

    def validate(self, data):
        # Validate that structured agents have a schema definition
        if data.get('return_type') == 'structured' and not data.get('schema_definition'):
            raise serializers.ValidationError({
                'schema_definition': 'Schema definition is required for structured return type.'
            })
        return data

    @transaction.atomic
    def create(self, validated_data):
        prompts_data = validated_data.pop('prompts', [])
        tool_ids = validated_data.pop('tool_ids', [])

        # Set created_by from request context
        validated_data['created_by'] = self.context['request'].user

        # Create the agent
        agent = Agent.objects.create(**validated_data)

        # Create prompts
        for prompt_data in prompts_data:
            Prompt.objects.create(
                agent=agent,
                created_by=self.context['request'].user,
                **prompt_data
            )

        # Link tools
        for tool_id in tool_ids:
            AgentTool.objects.create(
                agent=agent,
                tool_id=tool_id,
                created_by=self.context['request'].user,
                configuration={}
            )

        return agent