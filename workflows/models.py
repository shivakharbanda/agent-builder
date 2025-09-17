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
    """Orchestrates agents and data processing"""
    STATUS_CHOICES = [
        ('draft', 'Draft'),
        ('active', 'Active'),
        ('paused', 'Paused'),
        ('completed', 'Completed'),
    ]

    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='workflows')
    configuration = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='draft')

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    class Meta:
        db_table = 'workflows_workflow'
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
    position = models.PositiveIntegerField()
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
