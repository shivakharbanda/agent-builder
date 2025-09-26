from rest_framework import viewsets, filters, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from .models import Agent, Prompt, Tool, AgentTool
from .serializers import (
    AgentSerializer, AgentListSerializer, PromptSerializer,
    ToolSerializer, AgentToolSerializer, AgentCompleteCreateSerializer
)


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
