from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import Project
from .serializers import ProjectSerializer, ProjectListSerializer
from agents.models import Agent
from agents.serializers import AgentListSerializer
from workflows.models import Workflow
from workflows.serializers import WorkflowListSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.filter(is_active=True)
    serializer_class = ProjectSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return ProjectListSerializer
        return ProjectSerializer

    @action(detail=True, methods=['get'])
    def agents(self, request, pk=None):
        """Get all agents for this project"""
        project = self.get_object()
        agents = Agent.objects.filter(project=project, is_active=True)
        serializer = AgentListSerializer(agents, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def workflows(self, request, pk=None):
        """Get all workflows for this project"""
        project = self.get_object()
        workflows = Workflow.objects.filter(project=project, is_active=True)
        serializer = WorkflowListSerializer(workflows, many=True)
        return Response(serializer.data)
