from django.db import models
from common.models import BaseModel
from projects.models import Project


class Agent(BaseModel):
    """AI agents that process data through workflows"""
    RETURN_TYPE_CHOICES = [
        ('structured', 'Structured'),
        ('unstructured', 'Unstructured'),
    ]

    name = models.CharField(max_length=200, unique=True)
    description = models.TextField(blank=True)
    return_type = models.CharField(max_length=20, choices=RETURN_TYPE_CHOICES)
    schema_definition = models.JSONField(null=True, blank=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='agents')

    def __str__(self):
        return f"{self.name} ({self.project.name})"

    class Meta:
        db_table = 'agents_agent'
        ordering = ['-created_at']


class Prompt(BaseModel):
    """System and user prompts that belong to specific agents"""
    PROMPT_TYPE_CHOICES = [
        ('system', 'System'),
        ('user', 'User'),
    ]

    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='prompts')
    prompt_type = models.CharField(max_length=10, choices=PROMPT_TYPE_CHOICES)
    content = models.TextField()
    placeholders = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.prompt_type.title()} prompt for {self.agent.name}"

    class Meta:
        db_table = 'agents_prompt'
        ordering = ['prompt_type']
        unique_together = ['agent', 'prompt_type']


class Tool(BaseModel):
    """External tools/APIs that agents can use"""
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    tool_type = models.CharField(max_length=100)
    configuration = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'agents_tool'
        ordering = ['name']


class AgentTool(BaseModel):
    """Many-to-many relationship between agents and tools"""
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='agent_tools')
    tool = models.ForeignKey(Tool, on_delete=models.CASCADE, related_name='agent_tools')
    configuration = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return f"{self.agent.name} - {self.tool.name}"

    class Meta:
        db_table = 'agents_agent_tool'
        unique_together = ['agent', 'tool']
