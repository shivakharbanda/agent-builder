from rest_framework import viewsets, filters, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from .models import Agent, Prompt, Tool, AgentTool, MCPServer, MCPToolDefinition, AgentMCPServer
from .serializers import (
    AgentSerializer, AgentListSerializer, PromptSerializer,
    ToolSerializer, AgentToolSerializer, AgentCompleteCreateSerializer,
    AgentTestRequestSerializer, AgentTestResponseSerializer,
    MCPServerSerializer, MCPServerListSerializer, MCPToolDefinitionSerializer,
    AgentMCPServerSerializer
)
import asyncio


class AgentViewSet(viewsets.ModelViewSet):
    queryset = Agent.objects.filter(is_active=True)
    serializer_class = AgentSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'return_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return AgentListSerializer
        return AgentSerializer

    @action(detail=True, methods=['get'])
    def prompts(self, request, pk=None):
        """Get all prompts for this agent"""
        agent = self.get_object()
        prompts = Prompt.objects.filter(agent=agent, is_active=True)
        serializer = PromptSerializer(prompts, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def tools(self, request, pk=None):
        """Get all tools for this agent"""
        agent = self.get_object()
        agent_tools = AgentTool.objects.filter(agent=agent, is_active=True)
        serializer = AgentToolSerializer(agent_tools, many=True)
        return Response(serializer.data)


class PromptViewSet(viewsets.ModelViewSet):
    queryset = Prompt.objects.filter(is_active=True)
    serializer_class = PromptSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['agent', 'prompt_type', 'is_active']
    search_fields = ['content']
    ordering_fields = ['prompt_type', 'created_at']
    ordering = ['prompt_type']


class ToolViewSet(viewsets.ModelViewSet):
    queryset = Tool.objects.filter(is_active=True)
    serializer_class = ToolSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['tool_type', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class AgentToolViewSet(viewsets.ModelViewSet):
    queryset = AgentTool.objects.filter(is_active=True)
    serializer_class = AgentToolSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['agent', 'tool', 'is_active']
    ordering_fields = ['created_at']
    ordering = ['-created_at']


class CreateAgentCompleteView(APIView):
    """Create agent with prompts and tools in a single atomic operation"""

    def post(self, request):
        serializer = AgentCompleteCreateSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        agent = serializer.save()

        # Return the full agent data using the standard serializer
        response_serializer = AgentSerializer(agent, context={'request': request})
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)


class TestAgentView(APIView):
    """
    Test an agent with provided inputs.

    Supports both structured and unstructured agent testing.
    """

    def post(self, request, pk):
        """
        Execute agent test.

        Args:
            pk: Agent ID
            request.data: Test request containing test_type and inputs

        Returns:
            Test results with agent output
        """
        from .services import AgentExecutor, ConversationManager

        # Validate request
        request_serializer = AgentTestRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        test_data = request_serializer.validated_data
        test_type = test_data['test_type']
        credential_id = test_data['credential_id']
        model = test_data.get('model', None)

        try:
            # Initialize executor
            executor = AgentExecutor(agent_id=pk)

            # Execute based on test type
            if test_type == 'structured':
                inputs = test_data.get('inputs', {})
                result = executor.execute_structured(
                    placeholder_values=inputs,
                    credential_id=credential_id,
                    model=model
                )

            else:  # unstructured
                message = test_data.get('message')
                conversation_history = test_data.get('conversation_history', [])

                # Validate conversation history
                conversation_history = ConversationManager.validate_history(conversation_history)

                result = executor.execute_unstructured(
                    message=message,
                    credential_id=credential_id,
                    conversation_history=conversation_history,
                    model=model
                )

            # Serialize response
            response_serializer = AgentTestResponseSerializer(data=result)
            response_serializer.is_valid(raise_exception=True)

            return Response(response_serializer.data, status=status.HTTP_200_OK)

        except Agent.DoesNotExist:
            return Response(
                {'error': f'Agent with ID {pk} not found'},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {
                    'success': False,
                    'error': str(e),
                    'execution_time_ms': 0
                },
                status=status.HTTP_400_BAD_REQUEST
            )


# ============================================================================
# MCP (Model Context Protocol) ViewSets
# ============================================================================

class MCPServerViewSet(viewsets.ModelViewSet):
    """ViewSet for managing MCP servers"""
    queryset = MCPServer.objects.filter(is_active=True)
    serializer_class = MCPServerSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['transport', 'is_healthy', 'is_active']
    search_fields = ['name', 'description', 'url']
    ordering_fields = ['name', 'created_at', 'last_schema_sync']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return MCPServerListSerializer
        return MCPServerSerializer

    @action(detail=False, methods=['post'])
    def test_connection(self, request):
        """Test connection to MCP server URL"""
        from .services.mcp_discovery import MCPDiscoveryService

        url = request.data.get('url')
        if not url:
            return Response(
                {"error": "URL required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            result = asyncio.run(MCPDiscoveryService.test_connection(url))
            return Response(result)
        except Exception as e:
            return Response(
                {"healthy": False, "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'])
    def discover_tools(self, request):
        """Discover tools from MCP server URL without saving"""
        from .services.mcp_discovery import MCPDiscoveryService

        url = request.data.get('url')
        if not url:
            return Response(
                {"error": "URL required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        tool_prefix = request.data.get('tool_prefix', '')

        try:
            result = asyncio.run(MCPDiscoveryService.discover_tools(url, tool_prefix))
            return Response(result)
        except Exception as e:
            return Response(
                {"healthy": False, "tools": [], "error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['post'])
    def sync_schema(self, request, pk=None):
        """Sync tool definitions from MCP server"""
        from .services.mcp_discovery import MCPDiscoveryService

        try:
            result = asyncio.run(MCPDiscoveryService.sync_server_schema(int(pk)))
            return Response(result)
        except Exception as e:
            return Response(
                {"error": str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=True, methods=['get'])
    def tools(self, request, pk=None):
        """Get all tools from this server"""
        server = self.get_object()
        tools = server.tools.all()
        serializer = MCPToolDefinitionSerializer(tools, many=True)
        return Response(serializer.data)


class AgentMCPServerViewSet(viewsets.ModelViewSet):
    """ViewSet for managing agent-MCP server relationships"""
    queryset = AgentMCPServer.objects.filter(is_active=True)
    serializer_class = AgentMCPServerSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['agent', 'mcp_server', 'is_active']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

