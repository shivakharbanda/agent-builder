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


class MCPServer(BaseModel):
    """MCP (Model Context Protocol) server registry"""
    TRANSPORT_CHOICES = [
        ('sse', 'Server-Sent Events'),
        ('stdio', 'Standard I/O'),
        ('http', 'Streamable HTTP'),
    ]

    name = models.CharField(max_length=200, help_text="Friendly name (e.g., 'Crawl4AI Production')")
    description = models.TextField(blank=True, help_text="What this server provides")
    url = models.URLField(help_text="MCP endpoint URL (e.g., https://crawl4ai.../mcp/sse)")
    transport = models.CharField(max_length=20, choices=TRANSPORT_CHOICES, default='sse')
    tool_prefix = models.CharField(max_length=50, blank=True, help_text="Prefix for tool names (e.g., 'c4ai')")

    # Connection health
    is_healthy = models.BooleanField(default=True)
    last_schema_sync = models.DateTimeField(null=True, blank=True)

    # Optional auth (for future)
    auth_config = models.JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'agents_mcp_server'
        ordering = ['name']


class MCPToolDefinition(BaseModel):
    """Tool definitions discovered from MCP servers"""
    server = models.ForeignKey(MCPServer, on_delete=models.CASCADE, related_name='tools')

    # Standard MCP schema fields
    name = models.CharField(max_length=200, help_text="Tool name from MCP server (e.g., 'md')")
    prefixed_name = models.CharField(max_length=200, help_text="With prefix (e.g., 'c4ai_md')")
    title = models.CharField(max_length=200, blank=True)
    description = models.TextField(blank=True)

    # JSON schemas
    input_schema = models.JSONField(default=dict, help_text="Tool input schema (from MCP)")
    output_schema = models.JSONField(default=dict, null=True, blank=True)
    annotations = models.JSONField(default=dict, null=True, blank=True)
    meta = models.JSONField(default=dict, null=True, blank=True)

    # For AI-assisted workflow building
    capabilities_tags = models.JSONField(default=list, blank=True, help_text="Auto-extracted capabilities")
    required_inputs = models.JSONField(default=list, blank=True, help_text="Required input fields")

    def __str__(self):
        return f"{self.server.name} - {self.prefixed_name}"

    class Meta:
        db_table = 'agents_mcp_tool_definition'
        ordering = ['server', 'name']
        unique_together = [['server', 'name']]


class AgentMCPServer(BaseModel):
    """Link agents to MCP servers (many-to-many)"""
    agent = models.ForeignKey(Agent, on_delete=models.CASCADE, related_name='mcp_servers')
    mcp_server = models.ForeignKey(MCPServer, on_delete=models.CASCADE, related_name='agents')

    # Optional per-agent overrides
    custom_tool_prefix = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"{self.agent.name} - {self.mcp_server.name}"

    class Meta:
        db_table = 'agents_agent_mcp_server'
        unique_together = [['agent', 'mcp_server']]
