from django.db import models
from common.models import BaseModel
from projects.models import Project
from agents.models import Agent


class DataSource(BaseModel):
    """Define data inputs (call transcripts, etc.)"""
    LOAD_MODE_CHOICES = [
        ('full', 'Full Load'),
        ('incremental', 'Incremental Load'),
    ]

    SOURCE_TYPE_CHOICES = [
        ('database', 'Database'),
        ('file', 'File'),
        ('api', 'API'),
    ]

    name = models.CharField(max_length=200)
    source_type = models.CharField(max_length=20, choices=SOURCE_TYPE_CHOICES)
    connection_config = models.JSONField(default=dict)
    load_mode = models.CharField(max_length=20, choices=LOAD_MODE_CHOICES)
    watermark_start_date = models.DateTimeField(null=True, blank=True)
    watermark_end_date = models.DateTimeField(null=True, blank=True)
    table_name = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'workflows_data_source'
        ordering = ['name']


class Workflow(BaseModel):
    """Orchestrates agents and data processing - core workflow definition"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='workflows')
    configuration = models.JSONField(default=dict, blank=True)  # Only nodes/edges/metadata

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    class Meta:
        db_table = 'workflows_workflow'
        ordering = ['-created_at']


class WorkflowProperties(BaseModel):
    """Scheduling and orchestration properties for workflows"""
    workflow = models.OneToOneField(Workflow, on_delete=models.CASCADE, related_name='properties')
    watermark_start_date = models.DateTimeField(null=True, blank=True)
    watermark_end_date = models.DateTimeField(null=True, blank=True)
    schedule = models.CharField(max_length=100, blank=True, help_text="Cron expression for scheduling")
    timeout = models.PositiveIntegerField(default=3600, help_text="Timeout in seconds")
    retry_count = models.PositiveIntegerField(default=3, help_text="Number of retry attempts")
    notification_email = models.EmailField(blank=True, help_text="Email for notifications")

    def __str__(self):
        return f"Properties for {self.workflow.name}"

    class Meta:
        db_table = 'workflows_workflow_properties'
        ordering = ['workflow__name']


class WorkflowExecution(BaseModel):
    """Execution tracking and status for workflow runs"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('running', 'Running'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]

    TRIGGER_CHOICES = [
        ('manual', 'Manual'),
        ('schedule', 'Scheduled'),
        ('api', 'API'),
        ('webhook', 'Webhook'),
    ]

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='executions')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    execution_log = models.JSONField(default=dict, blank=True)
    error_message = models.TextField(blank=True)
    triggered_by = models.CharField(max_length=20, choices=TRIGGER_CHOICES, default='manual')

    def __str__(self):
        return f"{self.workflow.name} - {self.status} ({self.created_at})"

    class Meta:
        db_table = 'workflows_workflow_execution'
        ordering = ['-created_at']


class WorkflowNode(BaseModel):
    """Individual steps in workflow (data input → agent → output)"""
    NODE_TYPE_CHOICES = [
        ('input', 'Input'),
        ('agent', 'Agent'),
        ('output', 'Output'),
    ]

    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='nodes')
    node_type = models.CharField(max_length=10, choices=NODE_TYPE_CHOICES)
    position = models.PositiveIntegerField()  # Order position
    visual_position = models.JSONField(default=dict, blank=True, help_text="Canvas position as {x, y}")  # Canvas position
    configuration = models.JSONField(default=dict, blank=True)
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, null=True, blank=True)
    data_source = models.ForeignKey(DataSource, on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"{self.workflow.name} - {self.node_type} (pos: {self.position})"

    class Meta:
        db_table = 'workflows_workflow_node'
        ordering = ['workflow', 'position']
        unique_together = ['workflow', 'position']


class PlaceholderMapping(BaseModel):
    """Map data table columns to agent prompt placeholders"""
    workflow_node = models.ForeignKey(WorkflowNode, on_delete=models.CASCADE, related_name='placeholder_mappings')
    placeholder_name = models.CharField(max_length=200)
    data_column = models.CharField(max_length=200)
    transformation = models.CharField(max_length=500, blank=True)

    def __str__(self):
        return f"{self.placeholder_name} -> {self.data_column}"

    class Meta:
        db_table = 'workflows_placeholder_mapping'
        unique_together = ['workflow_node', 'placeholder_name']


class OutputNode(BaseModel):
    """Save agent output to specified destination"""
    workflow = models.ForeignKey(Workflow, on_delete=models.CASCADE, related_name='output_nodes')
    destination_table = models.CharField(max_length=200)
    configuration = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.workflow.name} -> {self.destination_table}"

    class Meta:
        db_table = 'workflows_output_node'


# ============================================================================
# Node Registry Models
# ============================================================================

class NodeCategory(BaseModel):
    """
    Node categories for organizing node types.

    Examples: data_source, processor, data_sink, control_flow
    """
    name = models.CharField(max_length=100, unique=True, help_text="Category identifier (e.g., data_source)")
    description = models.TextField(blank=True, help_text="Description of what this category represents")
    icon = models.CharField(max_length=50, blank=True, help_text="Icon identifier for UI")

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'workflows_node_category'
        ordering = ['name']
        verbose_name_plural = 'Node Categories'


class NodeType(BaseModel):
    """
    Node type definitions with handler class mappings.

    Stores metadata about each node type including:
    - Which handler class to instantiate
    - Display information (name, description, icon)
    - Category classification

    Examples:
        - database → DatabaseNode handler
        - agent → AgentNode handler
        - output → OutputNode handler

    TODO: Future expansions:
        - Add NodeConfigField model for dynamic field definitions
        - Add NodeInputOutput model for input/output specifications
        - Replace nodeConfigs.json with database-driven node definitions
    """
    category = models.ForeignKey(
        NodeCategory,
        on_delete=models.CASCADE,
        related_name='node_types',
        help_text="Category this node type belongs to"
    )
    type_name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Type identifier (e.g., database, agent)"
    )
    type_description = models.TextField(
        blank=True,
        help_text="Description of what this node type does"
    )
    icon = models.CharField(
        max_length=50,
        blank=True,
        help_text="Icon identifier for UI"
    )
    handler_class_name = models.CharField(
        max_length=200,
        help_text="Python class name of the node handler (e.g., DatabaseNode, AgentNode)"
    )

    def __str__(self):
        return f"{self.type_name} ({self.category.name})"

    class Meta:
        db_table = 'workflows_node_type'
        ordering = ['category', 'type_name']
