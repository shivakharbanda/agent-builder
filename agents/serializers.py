from rest_framework import serializers
from django.db import transaction
from .models import Agent, Prompt, Tool, AgentTool, MCPServer, MCPToolDefinition, AgentMCPServer


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
    input_placeholders = serializers.SerializerMethodField()

    class Meta:
        model = Agent
        fields = [
            'id', 'name', 'description', 'return_type', 'project_name',
            'prompts_count', 'tools_count', 'input_placeholders', 'created_at', 'is_active'
        ]

    def get_prompts_count(self, obj):
        return obj.prompts.filter(is_active=True).count()

    def get_tools_count(self, obj):
        return obj.agent_tools.filter(is_active=True).count()

    def get_input_placeholders(self, obj):
        """
        Extract all unique placeholders from agent prompts.
        Searches for {{placeholder_name}} patterns in prompt content.

        Returns:
            List of unique placeholder names found across all prompts
        """
        import re

        placeholders = set()

        # Get all active prompts for this agent
        prompts = obj.prompts.filter(is_active=True)

        for prompt in prompts:
            # Extract placeholders using regex pattern {{placeholder_name}}
            pattern = r'\{\{(\w+)\}\}'
            matches = re.findall(pattern, prompt.content)
            placeholders.update(matches)

        # Return sorted list for consistent ordering
        return sorted(list(placeholders))


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


class AgentTestRequestSerializer(serializers.Serializer):
    """Serializer for agent test requests"""
    test_type = serializers.ChoiceField(choices=['structured', 'unstructured'], required=True)
    credential_id = serializers.IntegerField(required=True, help_text="ID of LLM credential to use")
    model = serializers.CharField(
        required=False,
        allow_blank=True,
        help_text="Model name to use (e.g., 'gemini-1.5-flash', 'gpt-4o'). If not provided, uses default from credential."
    )

    # For structured tests
    inputs = serializers.JSONField(
        required=False,
        help_text="Placeholder values for structured agent testing"
    )

    # For unstructured tests
    message = serializers.CharField(
        required=False,
        allow_blank=False,
        help_text="User message for unstructured agent testing"
    )
    conversation_history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list,
        help_text="Conversation history for unstructured agent"
    )

    def validate(self, data):
        """Validate that required fields are present based on test_type"""
        test_type = data.get('test_type')

        if test_type == 'structured':
            if 'inputs' not in data:
                raise serializers.ValidationError({
                    'inputs': 'Required for structured agent testing'
                })

        elif test_type == 'unstructured':
            if 'message' not in data:
                raise serializers.ValidationError({
                    'message': 'Required for unstructured agent testing'
                })

        return data


class AgentTestResponseSerializer(serializers.Serializer):
    """Serializer for agent test responses"""
    success = serializers.BooleanField()
    execution_time_ms = serializers.IntegerField()
    error = serializers.CharField(required=False, allow_null=True)

    # For structured responses
    output = serializers.JSONField(required=False, allow_null=True)

    # For unstructured responses
    response = serializers.CharField(required=False, allow_null=True)
    conversation_history = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=list
    )


# ============================================================================
# MCP (Model Context Protocol) Serializers
# ============================================================================

class MCPToolDefinitionSerializer(serializers.ModelSerializer):
    """Serializer for MCP tool definitions"""
    class Meta:
        model = MCPToolDefinition
        fields = [
            'id', 'name', 'prefixed_name', 'title', 'description',
            'input_schema', 'output_schema', 'capabilities_tags',
            'required_inputs', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class MCPServerSerializer(serializers.ModelSerializer):
    """Serializer for MCP servers with tool definitions"""
    tools = MCPToolDefinitionSerializer(many=True, read_only=True)
    tools_count = serializers.SerializerMethodField()

    class Meta:
        model = MCPServer
        fields = [
            'id', 'name', 'description', 'url', 'transport', 'tool_prefix',
            'is_healthy', 'last_schema_sync', 'tools_count', 'tools',
            'created_at', 'updated_at', 'created_by', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by', 'is_healthy', 'last_schema_sync']

    def get_tools_count(self, obj):
        return obj.tools.count()

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class MCPServerListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for MCP server lists"""
    tools_count = serializers.SerializerMethodField()

    class Meta:
        model = MCPServer
        fields = [
            'id', 'name', 'description', 'url', 'transport', 'tool_prefix',
            'is_healthy', 'last_schema_sync', 'tools_count', 'created_at', 'is_active'
        ]

    def get_tools_count(self, obj):
        return obj.tools.count()


class AgentMCPServerSerializer(serializers.ModelSerializer):
    """Serializer for agent-MCP server relationships"""
    server_name = serializers.CharField(source='mcp_server.name', read_only=True)
    server_url = serializers.CharField(source='mcp_server.url', read_only=True)
    tools_count = serializers.SerializerMethodField()

    class Meta:
        model = AgentMCPServer
        fields = [
            'id', 'agent', 'mcp_server', 'server_name', 'server_url',
            'custom_tool_prefix', 'tools_count', 'created_at', 'is_active'
        ]
        read_only_fields = ['id', 'created_at', 'server_name', 'server_url', 'tools_count']

    def get_tools_count(self, obj):
        return obj.mcp_server.tools.count()

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)