"""
Workflow Handler

This module contains the WorkflowHandler class responsible for managing
and executing workflows.
"""

from workflows.models import Workflow
from workflows.serializers import WorkflowSerializer


class WorkflowHandler:
    """
    Handles workflow execution and management.

    Can be initialized with either a workflow_id or a workflow_config dict.
    If workflow_id is provided, it fetches the complete workflow configuration
    from the database.

    Attributes:
        workflow_id (int): The ID of the workflow
        workflow_name (str): Name of the workflow
        workflow_description (str): Description of the workflow
        configuration (dict): The workflow configuration (nodes and edges)
        nodes (list): List of workflow nodes
        edges (list): List of workflow edges
        properties (dict): Workflow properties (schedule, timeout, etc.)
        project_id (int): ID of the associated project
        project_name (str): Name of the associated project
    """

    def __init__(self, workflow_id=None, workflow_config=None):
        """
        Initialize the WorkflowHandler.

        Args:
            workflow_id (int, optional): ID of the workflow to load from database
            workflow_config (dict, optional): Pre-loaded workflow configuration

        Raises:
            ValueError: If neither or both parameters are provided
            Workflow.DoesNotExist: If workflow_id is provided but not found in database
        """
        # Validation: must provide exactly one parameter
        if workflow_id is None and workflow_config is None:
            raise ValueError("Must provide either workflow_id or workflow_config")

        if workflow_id is not None and workflow_config is not None:
            raise ValueError("Cannot provide both workflow_id and workflow_config")

        # Initialize attributes
        self.workflow_id = None
        self.workflow_name = None
        self.workflow_description = None
        self.configuration = {}
        self.nodes = []
        self.edges = []
        self.properties = {}
        self.project_id = None
        self.project_name = None
        self._raw_workflow_data = None

        # Load workflow data
        if workflow_id is not None:
            self._load_from_database(workflow_id)
        else:
            self._load_from_config(workflow_config)

    def _load_from_database(self, workflow_id):
        """
        Load workflow data from database using workflow_id.

        Args:
            workflow_id (int): The workflow ID to fetch

        Raises:
            Workflow.DoesNotExist: If workflow not found
        """
        # Fetch workflow from database
        workflow = Workflow.objects.get(id=workflow_id, is_active=True)

        # Serialize to get the same structure as API endpoint
        serializer = WorkflowSerializer(workflow)
        workflow_data = serializer.data

        # Store raw data
        self._raw_workflow_data = workflow_data

        # Extract and store workflow attributes
        self._extract_workflow_data(workflow_data)

    def _load_from_config(self, workflow_config):
        """
        Load workflow data from a pre-loaded configuration dict.

        Args:
            workflow_config (dict): The workflow configuration dictionary
        """
        # Store raw data
        self._raw_workflow_data = workflow_config

        # Extract and store workflow attributes
        self._extract_workflow_data(workflow_config)

    def _extract_workflow_data(self, workflow_data):
        """
        Extract and store workflow data from the configuration dict.

        Args:
            workflow_data (dict): The workflow data dictionary
        """
        # Basic workflow info
        self.workflow_id = workflow_data.get('id')
        self.workflow_name = workflow_data.get('name')
        self.workflow_description = workflow_data.get('description', '')

        # Configuration (nodes and edges in React Flow format)
        self.configuration = workflow_data.get('configuration', {})

        # Extract nodes and edges from configuration
        self.nodes = self.configuration.get('nodes', [])
        self.edges = self.configuration.get('edges', [])

        # Workflow properties (schedule, timeout, etc.)
        self.properties = workflow_data.get('properties', {})

        # Project information
        self.project_id = workflow_data.get('project')
        self.project_name = workflow_data.get('project_name', '')

    def get_workflow_config(self):
        """
        Get the complete workflow configuration.

        Returns:
            dict: Complete workflow configuration including all metadata
        """
        return {
            'id': self.workflow_id,
            'name': self.workflow_name,
            'description': self.workflow_description,
            'configuration': self.configuration,
            'nodes': self.nodes,
            'edges': self.edges,
            'properties': self.properties,
            'project_id': self.project_id,
            'project_name': self.project_name,
        }

    def get_raw_data(self):
        """
        Get the raw workflow data as received from database or config.

        Returns:
            dict: Raw workflow data
        """
        return self._raw_workflow_data

    def __repr__(self):
        """String representation of WorkflowHandler."""
        return f"<WorkflowHandler(id={self.workflow_id}, name='{self.workflow_name}', nodes={len(self.nodes)})>"

    def __str__(self):
        """Human-readable string representation."""
        return f"WorkflowHandler for '{self.workflow_name}' (ID: {self.workflow_id})"
