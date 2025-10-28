"""
Structured response models for workflow builder agent.

These models define the union output type for the agent,
allowing it to return either conversational responses or workflow actions.
"""

from pydantic import BaseModel, Field


class ConversationalResponse(BaseModel):
    """
    Simple conversational message response.

    Used when user is having normal conversation (greetings, questions, help).
    """
    message: str = Field(
        description="Friendly response message to the user"
    )


class NodePosition(BaseModel):
    """Canvas position with x and y coordinates."""
    x: float = Field(description="X coordinate on canvas")
    y: float = Field(description="Y coordinate on canvas")


class NodeConfig(BaseModel):
    """
    Workflow node configuration.

    Defines the structure and settings for a workflow node.
    """
    node_type: str = Field(
        description="Type of node (trigger_manual, trigger_schedule, trigger_chat, database, agent, toolbox, filter, script, conditional, output)"
    )
    position: NodePosition = Field(
        description="Canvas position for the node"
    )
    config: dict = Field(
        default_factory=dict,
        description="Node-specific configuration (credential_id, query, schedule, etc.)"
    )
    label: str | None = Field(
        default=None,
        description="Optional human-readable label for the node"
    )


class NodeAddAction(BaseModel):
    """
    Action to add a new node to the workflow.

    Used when user explicitly requests to add a node
    (e.g., "I need a manual trigger", "add a database node").
    """
    node_id: str = Field(
        description="Unique node identifier (e.g., 'trigger-1', 'database-1')"
    )
    node: NodeConfig = Field(
        description="Complete node configuration"
    )
    message: str = Field(
        description="Confirmation message to display to user"
    )


class EdgeAddAction(BaseModel):
    """
    Action to add an edge (connection) between two nodes.

    Used when user requests to connect nodes
    (e.g., "connect trigger-1 to agent-1", "connect database-1 to agent-1 context").
    """
    source_node_id: str = Field(
        description="Source node identifier (e.g., 'trigger-1')"
    )
    target_node_id: str = Field(
        description="Target node identifier (e.g., 'agent-1')"
    )
    source_handle: str | None = Field(
        default=None,
        description="Source handle ID (e.g., 'true', 'false' for conditional nodes, None for default)"
    )
    target_handle: str | None = Field(
        default=None,
        description="Target handle ID (e.g., 'data-input', 'context-input', 'tools-input' for agent nodes, None for default)"
    )
    message: str = Field(
        description="Confirmation message to display to user"
    )


class NodeRemoveAction(BaseModel):
    """
    Action to remove a node from the workflow.

    Used when user requests to delete a node
    (e.g., "remove the trigger", "delete the agent node").
    """
    node_id: str = Field(
        description="Node identifier to remove (use exact ID from workflow state)"
    )
    message: str = Field(
        description="Confirmation message to display to user"
    )


class EdgeRemoveAction(BaseModel):
    """
    Action to remove an edge (connection) between two nodes.

    Used when user requests to disconnect nodes
    (e.g., "disconnect trigger from agent", "remove the edge between X and Y").
    """
    source_node_id: str = Field(
        description="Source node identifier (use exact ID from workflow state)"
    )
    target_node_id: str = Field(
        description="Target node identifier (use exact ID from workflow state)"
    )
    source_handle: str | None = Field(
        default=None,
        description="Source handle ID (e.g., 'true', 'false' for conditional nodes, None for default)"
    )
    target_handle: str | None = Field(
        default=None,
        description="Target handle ID (e.g., 'data-input', 'context-input', 'tools-input', None for default)"
    )
    message: str = Field(
        description="Confirmation message to display to user"
    )
