from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import DataSource, Workflow, WorkflowNode, PlaceholderMapping, OutputNode
from .serializers import (
    DataSourceSerializer, WorkflowSerializer, WorkflowListSerializer,
    WorkflowNodeSerializer, PlaceholderMappingSerializer, OutputNodeSerializer
)


class DataSourceViewSet(viewsets.ModelViewSet):
    queryset = DataSource.objects.filter(is_active=True)
    serializer_class = DataSourceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['source_type', 'load_mode', 'is_active']
    search_fields = ['name', 'table_name']
    ordering_fields = ['name', 'created_at']
    ordering = ['name']


class WorkflowViewSet(viewsets.ModelViewSet):
    queryset = Workflow.objects.filter(is_active=True)
    serializer_class = WorkflowSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project', 'status', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'created_at']
    ordering = ['-created_at']

    def get_serializer_class(self):
        if self.action == 'list':
            return WorkflowListSerializer
        return WorkflowSerializer

    @action(detail=True, methods=['get'])
    def nodes(self, request, pk=None):
        """Get all nodes for this workflow"""
        workflow = self.get_object()
        nodes = WorkflowNode.objects.filter(workflow=workflow, is_active=True).order_by('position')
        serializer = WorkflowNodeSerializer(nodes, many=True)
        return Response(serializer.data)


class WorkflowNodeViewSet(viewsets.ModelViewSet):
    queryset = WorkflowNode.objects.filter(is_active=True)
    serializer_class = WorkflowNodeSerializer
    filter_backends = [DjangoFilterBackend, filters.OrderingFilter]
    filterset_fields = ['workflow', 'node_type', 'agent', 'data_source', 'is_active']
    ordering_fields = ['workflow', 'position', 'created_at']
    ordering = ['workflow', 'position']

    @action(detail=True, methods=['get'])
    def mappings(self, request, pk=None):
        """Get all placeholder mappings for this node"""
        node = self.get_object()
        mappings = PlaceholderMapping.objects.filter(workflow_node=node, is_active=True)
        serializer = PlaceholderMappingSerializer(mappings, many=True)
        return Response(serializer.data)


class PlaceholderMappingViewSet(viewsets.ModelViewSet):
    queryset = PlaceholderMapping.objects.filter(is_active=True)
    serializer_class = PlaceholderMappingSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['workflow_node', 'is_active']
    search_fields = ['placeholder_name', 'data_column']
    ordering_fields = ['placeholder_name', 'created_at']
    ordering = ['placeholder_name']


class OutputNodeViewSet(viewsets.ModelViewSet):
    queryset = OutputNode.objects.filter(is_active=True)
    serializer_class = OutputNodeSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['workflow', 'is_active']
    search_fields = ['destination_table']
    ordering_fields = ['destination_table', 'created_at']
    ordering = ['destination_table']
