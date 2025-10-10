from rest_framework import viewsets, filters, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from .models import (
    Agent, Prompt, Tool, AgentTool,
    MCPServer, MCPToolDefinition, AgentMCPServer,
    InternalTool, AgentInternalTool
)
from .serializers import (
    AgentSerializer, AgentListSerializer, PromptSerializer,
    ToolSerializer, AgentToolSerializer, AgentCompleteCreateSerializer,
    AgentTestRequestSerializer, AgentTestResponseSerializer,
    MCPServerSerializer, MCPServerListSerializer, MCPToolDefinitionSerializer,
    AgentMCPServerSerializer,
    InternalToolSerializer, InternalToolListSerializer, AgentInternalToolSerializer
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
        import uuid
        from .services import AgentExecutor, ConversationManager
        from .models import AgentTestSession
        from pydantic_ai.messages import ModelMessagesTypeAdapter

        # Validate request
        request_serializer = AgentTestRequestSerializer(data=request.data)
        request_serializer.is_valid(raise_exception=True)

        test_data = request_serializer.validated_data
        test_type = test_data['test_type']
        credential_id = test_data['credential_id']
        model = test_data.get('model', None)
        mcp_server_ids = test_data.get('mcp_server_ids', None)
        internal_tool_attachments = test_data.get('internal_tool_attachments', None)
        session_id = test_data.get('session_id', None)

        try:
            # Initialize executor
            executor = AgentExecutor(agent_id=pk)

            # Execute based on test type
            if test_type == 'structured':
                inputs = test_data.get('inputs', {})
                result = executor.execute_structured(
                    placeholder_values=inputs,
                    credential_id=credential_id,
                    model=model,
                    mcp_server_ids=mcp_server_ids,
                    internal_tool_attachments=internal_tool_attachments
                )

            else:  # unstructured
                message = test_data.get('message')

                # Session-based persistence (preferred method)
                if session_id:
                    # Get or create session
                    session, created = AgentTestSession.objects.get_or_create(
                        session_id=session_id,
                        defaults={
                            'agent_id': pk,
                            'created_by': request.user,
                            'message_history_blob': ''
                        }
                    )

                    # Load message history from blob
                    message_history = []
                    if session.message_history_blob:
                        try:
                            message_history = ModelMessagesTypeAdapter.validate_json(session.message_history_blob)
                        except Exception as e:
                            print(f"[TEST AGENT] Failed to deserialize message history: {e}")
                            message_history = []
                else:
                    # Fallback: use conversation_history from request (deprecated)
                    conversation_history = test_data.get('conversation_history', [])
                    conversation_history = ConversationManager.validate_history(conversation_history)
                    # Convert frontend format to PydanticAI format (this is lossy, prefer session_id)
                    message_history = conversation_history  # AgentExecutor will handle conversion
                    session_id = uuid.uuid4()  # Auto-generate for response

                # Execute agent
                result = executor.execute_unstructured(
                    message=message,
                    credential_id=credential_id,
                    message_history=message_history,
                    model=model,
                    mcp_server_ids=mcp_server_ids,
                    internal_tool_attachments=internal_tool_attachments
                )

                # Build conversation history for frontend
                if result['success']:
                    new_messages_json = result.get('new_messages_json', '')
                    if new_messages_json:
                        # Parse PydanticAI messages from this execution
                        new_messages = ModelMessagesTypeAdapter.validate_json(new_messages_json)

                        # CRITICAL FIX: Merge old message_history (from blob) with new_messages
                        # message_history was loaded earlier from session blob (lines 161-167)
                        all_messages = message_history + new_messages

                        # Serialize ALL messages (old + new) for storage
                        all_messages_json = ModelMessagesTypeAdapter.dump_json(all_messages).decode('utf-8')

                        # Save FULL conversation to session blob for persistence
                        if session_id:
                            session, created = AgentTestSession.objects.get_or_create(
                                session_id=session_id,
                                defaults={
                                    'agent_id': pk,
                                    'created_by': request.user,
                                    'message_history_blob': all_messages_json
                                }
                            )
                            if not created:
                                session.message_history_blob = all_messages_json
                                session.save()

                        # Convert ALL messages to conversation format for frontend
                        full_history = ConversationManager.messages_to_history(all_messages)
                        result['conversation_history'] = full_history
                    else:
                        result['conversation_history'] = []

                # Return session_id so frontend can continue conversation
                result['session_id'] = str(session_id)

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

        transport = request.data.get('transport', 'http')

        try:
            result = asyncio.run(MCPDiscoveryService.test_connection(url, transport))
            return Response(result)
        except Exception as e:
            return Response(
                {"healthy": False, "error": str(e), "tools_count": 0},
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
        transport = request.data.get('transport', 'http')

        try:
            result = asyncio.run(MCPDiscoveryService.discover_tools(url, tool_prefix, transport))
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


# ============================================================================
# Internal Tool ViewSets
# ============================================================================

class InternalToolViewSet(viewsets.ModelViewSet):
    """ViewSet for managing internal tools"""
    queryset = InternalTool.objects.filter(is_active=True)
    serializer_class = InternalToolSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'tool_type', 'requires_credential', 'is_enabled', 'is_active']
    search_fields = ['name', 'description', 'tool_type']
    ordering_fields = ['name', 'category', 'created_at']
    ordering = ['category', 'name']

    def get_serializer_class(self):
        if self.action == 'list':
            return InternalToolListSerializer
        return InternalToolSerializer

    @action(detail=False, methods=['get'])
    def registry(self, request):
        """Get all tools registered in the tool registry"""
        from agents.tools import get_all_tool_metadata

        try:
            tools_metadata = get_all_tool_metadata()
            return Response({
                'tools': tools_metadata,
                'count': len(tools_metadata)
            })
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['post'])
    def test_execute(self, request, pk=None):
        """Test tool execution with given credential and inputs"""
        from agents.tools import get_tool

        tool = self.get_object()

        # Get test parameters
        credential_id = request.data.get('credential_id')
        inputs = request.data.get('inputs', {})

        if not credential_id:
            return Response(
                {'error': 'credential_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get credential
        try:
            from credentials.models import Credential
            credential = Credential.objects.get(id=credential_id, is_active=True, is_deleted=False)
        except Credential.DoesNotExist:
            return Response(
                {'error': f'Credential {credential_id} not found or inactive'},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate credential type
        if tool.requires_credential and tool.required_credential_type:
            if credential.credential_type != tool.required_credential_type:
                return Response(
                    {
                        'error': f"Credential type mismatch: Tool requires '{tool.required_credential_type.type_name}', "
                                f"but credential is '{credential.credential_type.type_name}'"
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

        # Execute tool
        try:
            tool_class = get_tool(tool.tool_type)
            result = asyncio.run(tool_class.execute(credential, **inputs))

            return Response({
                'success': True,
                'result': result,
                'tool': tool.name,
                'inputs': inputs
            })

        except KeyError:
            return Response(
                {'error': f"Tool type '{tool.tool_type}' not found in registry"},
                status=status.HTTP_404_NOT_FOUND
            )
        except Exception as e:
            return Response(
                {'error': f'Tool execution failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AgentInternalToolViewSet(viewsets.ModelViewSet):
    """ViewSet for managing agent-internal tool relationships"""
    queryset = AgentInternalTool.objects.filter(is_active=True)
    serializer_class = AgentInternalToolSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['agent', 'tool', 'is_active']
    ordering_fields = ['created_at']
    ordering = ['-created_at']

