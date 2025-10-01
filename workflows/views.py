from rest_framework import viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend
from .models import DataSource, Workflow, WorkflowProperties, WorkflowExecution, WorkflowNode, PlaceholderMapping, OutputNode
from .serializers import (
    DataSourceSerializer, WorkflowSerializer, WorkflowListSerializer, WorkflowPropertiesSerializer, WorkflowExecutionSerializer,
    WorkflowNodeSerializer, PlaceholderMappingSerializer, OutputNodeSerializer
)
from .execution.handler import WorkflowHandler


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
    filterset_fields = ['project', 'is_active']
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

    @action(detail=True, methods=['get', 'put'])
    def properties(self, request, pk=None):
        """Get or update workflow properties"""
        workflow = self.get_object()

        # Get or create properties object
        properties, created = WorkflowProperties.objects.get_or_create(
            workflow=workflow,
            defaults={'created_by': request.user}
        )

        if request.method == 'GET':
            serializer = WorkflowPropertiesSerializer(properties)
            return Response(serializer.data)

        elif request.method == 'PUT':
            serializer = WorkflowPropertiesSerializer(properties, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)

    @action(detail=True, methods=['get', 'post'])
    def executions(self, request, pk=None):
        """Get workflow executions or create a new execution"""
        workflow = self.get_object()

        if request.method == 'GET':
            executions = workflow.executions.all()
            serializer = WorkflowExecutionSerializer(executions, many=True)
            return Response(serializer.data)

        elif request.method == 'POST':
            serializer = WorkflowExecutionSerializer(data=request.data)
            if serializer.is_valid():
                serializer.save(workflow=workflow, created_by=request.user)
                return Response(serializer.data, status=201)
            return Response(serializer.errors, status=400)

    @action(detail=True, methods=['post'])
    def execute(self, request, pk=None):
        """Execute workflow or a specific node within the workflow

        Request body:
        - {} - Execute full workflow
        - {"node_id": <id>} - Execute specific node only
        """
        from django.utils import timezone

        workflow = self.get_object()
        node_id = request.data.get('node_id')

        # Initialize WorkflowHandler to get complete workflow configuration
        try:
            handler = WorkflowHandler(workflow_id=workflow.id)
            workflow_config = handler.get_workflow_config()
        except Exception as e:
            return Response({
                'detail': f'Error loading workflow configuration: {str(e)}'
            }, status=500)

        # Validate node if node_id is provided
        if node_id:
            try:
                node = WorkflowNode.objects.get(id=node_id, workflow=workflow, is_active=True)
                # Single node execution mode
                response_data = {
                    'execution_id': 124,  # Hardcoded for now
                    'workflow_id': workflow.id,
                    'workflow_name': workflow.name,
                    'node_id': node.id,
                    'node_type': node.node_type,
                    'node_position': node.position,
                    'status': 'running',
                    'mode': 'single_node',
                    'started_at': timezone.now().isoformat(),
                    'message': f'Node execution started successfully for {node.node_type} node at position {node.position}',
                    'estimated_duration': '30 seconds',
                    'configuration': node.configuration,
                    'workflow_handler': {
                        'total_nodes': len(workflow_config['nodes']),
                        'total_edges': len(workflow_config['edges']),
                        'workflow_properties': workflow_config['properties']
                    }
                }
                return Response(response_data, status=202)
            except WorkflowNode.DoesNotExist:
                return Response({
                    'detail': f'Node with id {node_id} not found in workflow {workflow.id}'
                }, status=404)
        else:
            # Full workflow execution mode
            nodes = WorkflowNode.objects.filter(workflow=workflow, is_active=True).order_by('position')

            response_data = {
                'execution_id': 123,  # Hardcoded for now
                'workflow_id': workflow.id,
                'workflow_name': workflow.name,
                'status': 'running',
                'mode': 'full_workflow',
                'started_at': timezone.now().isoformat(),
                'message': 'Workflow execution started successfully',
                'total_nodes': len(workflow_config['nodes']),
                'nodes_to_execute': [node.id for node in nodes],
                'node_types': [node.node_type for node in nodes],
                'estimated_duration': '5 minutes',
                'execution_order': [
                    {
                        'position': node.position,
                        'node_id': node.id,
                        'node_type': node.node_type
                    }
                    for node in nodes
                ],
                'workflow_handler': {
                    'configuration': workflow_config['configuration'],
                    'properties': workflow_config['properties'],
                    'project_name': workflow_config['project_name']
                }
            }
            return Response(response_data, status=202)

    @action(detail=False, methods=['post'])
    def save_complete(self, request):
        """Save complete workflow with properties and nodes in single atomic transaction"""
        from django.db import transaction

        try:
            with transaction.atomic():
                # Extract data from request
                workflow_data = {
                    'name': request.data.get('name'),
                    'description': request.data.get('description', ''),
                    'project': request.data.get('project'),
                    'configuration': request.data.get('configuration', {})
                }

                properties_data = request.data.get('properties', {})

                # Create workflow
                workflow_serializer = WorkflowSerializer(data=workflow_data)
                if not workflow_serializer.is_valid():
                    return Response({
                        'workflow_errors': workflow_serializer.errors
                    }, status=400)

                workflow = workflow_serializer.save(created_by=request.user)

                # Create/update properties with flexible date handling
                properties_data_clean = self._clean_properties_data(properties_data)
                properties, created = WorkflowProperties.objects.get_or_create(
                    workflow=workflow,
                    defaults={**properties_data_clean, 'created_by': request.user}
                )

                if not created:
                    # Update existing properties
                    properties_serializer = WorkflowPropertiesSerializer(
                        properties, data=properties_data_clean, partial=True
                    )
                    if not properties_serializer.is_valid():
                        return Response({
                            'properties_errors': properties_serializer.errors
                        }, status=400)
                    properties_serializer.save()

                # Create initial execution record
                WorkflowExecution.objects.get_or_create(
                    workflow=workflow,
                    defaults={
                        'status': 'draft',
                        'created_by': request.user
                    }
                )

                # Create workflow nodes from configuration
                self._create_workflow_nodes_from_config(workflow, request.data.get('configuration', {}), request.user)

                # Return complete workflow data
                complete_serializer = WorkflowSerializer(workflow)
                return Response(complete_serializer.data, status=201)

        except Exception as e:
            return Response({
                'detail': f'Error saving workflow: {str(e)}'
            }, status=400)

    def _clean_properties_data(self, properties_data):
        """Clean and format properties data, especially dates"""
        from django.utils.dateparse import parse_datetime, parse_date
        from django.utils import timezone

        cleaned_data = properties_data.copy()

        # Handle date fields with Django's built-in parsing
        date_fields = ['watermark_start_date', 'watermark_end_date']
        for field in date_fields:
            if field in cleaned_data and cleaned_data[field]:
                try:
                    if isinstance(cleaned_data[field], str):
                        # Try Django's datetime parser first
                        parsed_date = parse_datetime(cleaned_data[field])
                        if not parsed_date:
                            # Try date parser if datetime fails
                            parsed_date_only = parse_date(cleaned_data[field])
                            if parsed_date_only:
                                # Convert date to datetime with timezone
                                parsed_date = timezone.make_aware(
                                    timezone.datetime.combine(parsed_date_only, timezone.datetime.min.time())
                                )

                        if parsed_date:
                            cleaned_data[field] = parsed_date.isoformat()
                        else:
                            cleaned_data[field] = None
                    elif cleaned_data[field] == '':
                        # Empty string becomes None
                        cleaned_data[field] = None
                except (ValueError, TypeError, AttributeError):
                    # If any parsing fails, set to None
                    cleaned_data[field] = None
            elif field in cleaned_data and cleaned_data[field] == '':
                # Handle empty strings
                cleaned_data[field] = None

        return cleaned_data

    def _create_workflow_nodes_from_config(self, workflow, configuration, user):
        """Create WorkflowNode records from configuration, avoiding duplicates"""
        nodes_data = configuration.get('nodes', [])

        # Clear existing nodes first
        WorkflowNode.objects.filter(workflow=workflow).delete()

        for index, node_data in enumerate(nodes_data):
            WorkflowNode.objects.create(
                workflow=workflow,
                node_type=node_data.get('type', 'input'),
                position=index,
                visual_position=node_data.get('position', {'x': 100 + index * 200, 'y': 100}),
                configuration=node_data.get('config', {}),
                created_by=user
            )

    @action(detail=True, methods=['put'])
    def update_complete(self, request, pk=None):
        """Update complete workflow atomically: workflow + properties + nodes"""
        from django.db import transaction

        try:
            with transaction.atomic():
                workflow = self.get_object()

                # Update main workflow fields
                workflow.name = request.data.get('name', workflow.name)
                workflow.description = request.data.get('description', workflow.description)
                workflow.configuration = request.data.get('configuration', workflow.configuration)
                workflow.save()

                # Update/Create properties atomically
                properties_data = request.data.get('properties', {})
                if properties_data:
                    properties_data_clean = self._clean_properties_data(properties_data)
                    properties, created = WorkflowProperties.objects.get_or_create(
                        workflow=workflow,
                        defaults={**properties_data_clean, 'created_by': request.user}
                    )

                    if not created:
                        # Update existing properties
                        for field, value in properties_data_clean.items():
                            setattr(properties, field, value)
                        properties.save()

                # Update workflow nodes from configuration
                self._update_workflow_nodes_from_config(workflow, request.data.get('configuration', {}), request.user)

                # Return complete workflow data
                complete_serializer = WorkflowSerializer(workflow)
                return Response(complete_serializer.data)

        except Exception as e:
            return Response({
                'detail': f'Error updating workflow: {str(e)}'
            }, status=400)

    def _update_workflow_nodes_from_config(self, workflow, configuration, user):
        """Update WorkflowNode records from configuration, replacing existing nodes"""
        nodes_data = configuration.get('nodes', [])

        # Clear existing nodes first (same pattern as create)
        WorkflowNode.objects.filter(workflow=workflow).delete()

        for index, node_data in enumerate(nodes_data):
            WorkflowNode.objects.create(
                workflow=workflow,
                node_type=node_data.get('type', 'input'),
                position=index,
                visual_position=node_data.get('position', {'x': 100 + index * 200, 'y': 100}),
                configuration=node_data.get('config', {}),
                created_by=user
            )


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
