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
        from workflows.execution.node_handlers.factory import NodeFactory

        workflow = self.get_object()
        node_id = request.data.get('node_id')

        # Debug logging
        print(f"DEBUG: Request data: {request.data}")
        print(f"DEBUG: node_id: {node_id}, type: {type(node_id)}")

        # Single node execution mode
        if node_id:
            try:
                # Get workflow node from database
                workflow_node = WorkflowNode.objects.get(id=node_id, workflow=workflow, is_active=True)

                # Create node instance using factory
                started_at = timezone.now()
                node_instance = NodeFactory.create_node(
                    node_id=workflow_node.id,
                    node_type=workflow_node.node_type,
                    configuration=workflow_node.configuration,
                    workflow_id=workflow.id,
                    execution_id=0,  # TODO: proper execution tracking
                    position=workflow_node.position
                )

                # Execute the node
                results = node_instance.run()
                completed_at = timezone.now()
                execution_time = (completed_at - started_at).total_seconds()

                # Get execution metadata
                metadata = node_instance.get_metadata()

                # Return successful execution results
                return Response({
                    'status': 'completed',
                    'node_id': node_id,
                    'node_type': workflow_node.node_type,
                    'workflow_id': workflow.id,
                    'workflow_name': workflow.name,
                    'results': results,
                    'metadata': metadata,
                    'started_at': started_at.isoformat(),
                    'completed_at': completed_at.isoformat(),
                    'execution_time': execution_time,
                    'message': f'{workflow_node.node_type.capitalize()} node executed successfully'
                }, status=200)

            except WorkflowNode.DoesNotExist:
                return Response({
                    'status': 'error',
                    'detail': f'Node with id {node_id} not found in workflow {workflow.id}'
                }, status=404)
            except ValueError as e:
                # Validation errors from node.validate()
                return Response({
                    'status': 'error',
                    'node_id': node_id,
                    'error': str(e),
                    'error_type': 'validation_error',
                    'message': 'Node validation failed'
                }, status=400)
            except Exception as e:
                # Runtime errors from node.execute()
                import traceback
                return Response({
                    'status': 'failed',
                    'node_id': node_id,
                    'error': str(e),
                    'error_type': type(e).__name__,
                    'traceback': traceback.format_exc() if request.user.is_staff else None,
                    'message': 'Node execution failed'
                }, status=500)

        # Full workflow execution mode
        else:
            return Response({
                'status': 'error',
                'detail': 'Full workflow execution not yet implemented. Please execute individual nodes.',
                'message': 'Use node_id parameter to execute a specific node'
            }, status=501)

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


# ============================================================================
# AI Workflow Builder Tool Endpoints
# ============================================================================

from django.db.models import Q
from credentials.models import Credential
from credentials.serializers import CredentialListSerializer
from agents.models import Agent
from agents.serializers import AgentListSerializer
from dq_db_manager.models.postgres import DataSourceMetadata
from workflows.authentication import SessionIDAuthentication
from rest_framework.permissions import IsAuthenticated


class WorkflowBuilderToolsViewSet(viewsets.ViewSet):
    """
    API endpoints for AI workflow builder tools.

    These endpoints are called by the Pydantic AI agent to gather context
    and resources needed for auto-configuring workflow nodes.

    Authentication:
    - register_session: Uses JWT authentication (called by UI/frontend)
    - Tool endpoints (get_credentials, get_agents, inspect_schema): Uses SessionIDAuthentication (called by FastAPI)
    """
    permission_classes = [IsAuthenticated]

    def get_authenticators(self):
        """
        Return different authentication classes based on the request path.

        register_session is called by the UI with JWT token to create a session.
        Tool endpoints (get_credentials, get_agents, inspect_schema) are called by:
          1. FastAPI with session_id parameter (SessionIDAuthentication)
          2. UI directly with JWT token (CustomAuthentication)

        We support both authentication methods for tool endpoints to allow:
        - AI agent tool calls from FastAPI (via session_id)
        - Direct UI calls for schema inspection, etc. (via JWT token)

        Note: We check the path instead of self.action because action is not yet
        available during the request initialization phase when this is called.
        """
        # Get the request - it's available even during initialization
        request = self.request if hasattr(self, 'request') else None

        if request and request.path.endswith('register_session/'):
            # This is register_session - UI calls with JWT token
            from users.authentication import CustomAuthentication
            from rest_framework.authentication import SessionAuthentication
            return [CustomAuthentication(), SessionAuthentication()]
        else:
            # Tool endpoints - support both FastAPI (session_id) and UI (JWT) calls
            from users.authentication import CustomAuthentication
            from rest_framework.authentication import SessionAuthentication
            return [
                SessionIDAuthentication(),  # Try session_id first (FastAPI agent tools)
                CustomAuthentication(),      # Fall back to JWT (UI direct calls)
                SessionAuthentication()      # Fall back to session cookie
            ]

    @action(detail=False, methods=['post'])
    def register_session(self, request):
        """
        Register a new workflow builder session.

        Request body:
            - project_id: Required project ID

        Returns:
            - session_id: UUID for the FastAPI session
        """
        import uuid
        from datetime import timedelta
        from django.utils import timezone
        from workflows.models import WorkflowBuilderSession

        project_id = request.data.get('project_id')

        if not project_id:
            return Response(
                {'error': 'project_id is required'},
                status=400
            )

        try:
            # Generate new session UUID
            session_id = uuid.uuid4()

            # Set expiration (24 hours from now)
            expires_at = timezone.now() + timedelta(hours=24)

            # Create session record
            session = WorkflowBuilderSession.objects.create(
                session_id=session_id,
                project_id=project_id,
                created_by=request.user,
                expires_at=expires_at,
                is_active=True
            )

            return Response({
                'session_id': str(session_id),
                'expires_at': expires_at.isoformat(),
                'project_id': project_id
            }, status=201)

        except Exception as e:
            return Response(
                {'error': f'Failed to create session: {str(e)}'},
                status=500
            )

    @action(detail=False, methods=['get'])
    def get_credentials(self, request):
        """
        Tool: Get available database credentials for the current user.

        Query params:
            - session_id: Optional workflow builder session ID (for FastAPI tools)
            - search: Optional search term to filter by name/description
            - category: Credential category filter (default: RDBMS)

        Returns:
            List of credentials matching the criteria
        """
        from workflows.models import WorkflowBuilderSession

        search = request.query_params.get('search', '')
        category = request.query_params.get('category', 'RDBMS')
        session_id = request.query_params.get('session_id')

        # Determine user: from session_id (FastAPI) or request.user (direct UI call)
        if session_id:
            try:
                session = WorkflowBuilderSession.objects.get(
                    session_id=session_id,
                    is_active=True
                )
                user = session.created_by
            except WorkflowBuilderSession.DoesNotExist:
                return Response(
                    {'error': f'Session {session_id} not found or expired'},
                    status=404
                )
        else:
            # Backward compatible: use request.user for direct UI calls
            user = request.user

        # Filter by user and category
        credentials = Credential.objects.filter(
            user=user,
            is_deleted=False,
            credential_type__category__name=category,
            is_active=True
        ).select_related('credential_type', 'credential_type__category')

        # Apply search filter if provided
        if search:
            credentials = credentials.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        serializer = CredentialListSerializer(credentials, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def get_agents(self, request):
        """
        Tool: Get available AI agents for a specific project.

        Query params:
            - session_id: Optional workflow builder session ID (for FastAPI tools)
            - project_id: Optional project ID (for direct UI calls, ignored if session_id provided)
            - search: Optional search term to filter by name/description

        Returns:
            List of agents matching the criteria
        """
        from workflows.models import WorkflowBuilderSession

        session_id = request.query_params.get('session_id')
        project_id = request.query_params.get('project_id')
        search = request.query_params.get('search', '')

        # Determine project: from session_id (FastAPI) or project_id param (direct UI call)
        if session_id:
            try:
                session = WorkflowBuilderSession.objects.get(
                    session_id=session_id,
                    is_active=True
                )
                project_id = session.project_id
            except WorkflowBuilderSession.DoesNotExist:
                return Response(
                    {'error': f'Session {session_id} not found or expired'},
                    status=404
                )
        elif not project_id:
            return Response(
                {'error': 'Either session_id or project_id is required'},
                status=400
            )

        # Filter by project
        agents = Agent.objects.filter(
            project_id=project_id,
            is_active=True
        )

        # Apply search filter if provided
        if search:
            agents = agents.filter(
                Q(name__icontains=search) | Q(description__icontains=search)
            )

        serializer = AgentListSerializer(agents, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def inspect_schema(self, request):
        """
        Tool: Inspect database schema for a credential.

        Request body:
            - credential_id: Required credential ID
            - session_id: Optional workflow builder session ID (for FastAPI tools)

        Returns:
            Database schema information (tables, columns, sample data)
        """
        from dq_db_manager.database_factory import DatabaseFactory
        from workflows.models import WorkflowBuilderSession

        credential_id = request.data.get('credential_id')
        session_id = request.data.get('session_id')

        if not credential_id:
            return Response(
                {'error': 'credential_id is required'},
                status=400
            )

        # Determine user: from session_id (FastAPI) or request.user (direct UI call)
        if session_id:
            try:
                session = WorkflowBuilderSession.objects.get(
                    session_id=session_id,
                    is_active=True
                )
                user = session.created_by
            except WorkflowBuilderSession.DoesNotExist:
                return Response(
                    {'error': f'Session {session_id} not found or expired'},
                    status=404
                )
        else:
            # Backward compatible: use request.user for direct UI calls
            user = request.user

        try:
            # Fetch credential - ensure it belongs to the determined user (security)
            credential = Credential.objects.select_related(
                'credential_type', 'credential_type__category'
            ).get(
                id=credential_id,
                user=user,
                is_deleted=False,
                is_active=True
            )

            # Verify it's a database credential
            if credential.credential_type.category.name != 'RDBMS':
                return Response(
                    {'error': f'Credential must be RDBMS type, got {credential.credential_type.category.name}'},
                    status=400
                )

            # Get connection details
            db_type = credential.credential_type.type_name.lower()
            connection_details = credential.get_connection_details()

            # Use dq_db_manager to extract metadata
            handler = DatabaseFactory.get_database_handler(db_type, connection_details)

            # Get complete metadata from dq_db_manager as dict
            metadata_dict = handler.metadata_extractor.get_complete_metadata()

            # Validate with DataSourceMetadata model
            metadata = DataSourceMetadata(**metadata_dict)

            # Return simple wrapper with credential info + validated metadata
            response_data = {
                'credential_id': credential.id,
                'credential_name': credential.name,
                'database_type': credential.credential_type.type_name,
                'metadata': metadata.model_dump()  # Convert Pydantic model to dict
            }

            return Response(response_data)

        except Credential.DoesNotExist:
            return Response(
                {'error': f'Credential {credential_id} not found or access denied'},
                status=404
            )
        except ValueError as e:
            return Response(
                {'error': f'Database type not supported: {str(e)}'},
                status=400
            )
        except Exception as e:
            return Response(
                {'error': f'Schema inspection failed: {str(e)}'},
                status=500
            )
