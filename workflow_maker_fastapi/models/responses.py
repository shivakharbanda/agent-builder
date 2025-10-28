"""
Structured response models for workflow builder agent.

These models define the structured outputs from the supervisor agent,
enabling the frontend to handle incremental workflow changes deterministically.
"""

from pydantic import BaseModel, Field
from typing import Literal, Optional, Any


class Position(BaseModel):
    """
    Canvas position with explicit x and y coordinates.

    This model ensures proper schema generation for AI models,
    avoiding the additionalProperties issue with dict[str, float].
    """
    x: float = Field(description="X coordinate on canvas")
    y: float = Field(description="Y coordinate on canvas")


class NodeAddAction(BaseModel):
    """
    Action to add a new node to the workflow.

    Note: This creates the node with position, label, AND complete configuration.
    Delegate to worker first to get resources, then add node with full config.

    Example:
        {
            "node_type": "database",
            "position": {"x": 400, "y": 200},
            "config": {
                "credential_id": 1,
                "query": "SELECT * FROM customers"
            },
            "label": "Customer Database"
        }
    """
    node_type: str = Field(
        description="Type of node to add (database, agent, filter, etc.)"
    )
    position: Position = Field(
        description="Canvas position with x and y coordinates"
    )
    config: dict[str, Any] = Field(
        default_factory=dict,
        description="Node configuration - should be complete with all required fields. Use worker to get resources before adding node."
    )
    label: Optional[str] = Field(
        default=None,
        description="Human-readable label for the node"
    )


class NodeEditAction(BaseModel):
    """
    Action to edit an existing node's configuration.

    Use ONLY for user-requested changes to existing nodes, NOT for initial configuration.
    Initial configuration should be done in node_add with full config.

    Only includes fields that need to be updated (partial update).

    Example:
        {
            "node_id": "node_123",
            "config_updates": {
                "query": "SELECT * FROM customers WHERE status = 'active'"
            }
        }
    """
    node_id: str = Field(
        description="ID of the node to edit"
    )
    config_updates: dict[str, Any] = Field(
        description="Partial config updates (only changed fields)"
    )
    position_update: Optional[Position] = Field(
        default=None,
        description="Optional position update with x and y coordinates"
    )


class NodeRemoveAction(BaseModel):
    """
    Action to remove a node from the workflow.

    Example:
        {
            "node_id": "node_456"
        }
    """
    node_id: str = Field(
        description="ID of the node to remove"
    )


class EdgeAddAction(BaseModel):
    """
    Action to add a new edge (connection) between nodes.

    Example:
        {
            "source": "node_1",
            "target": "node_2",
            "source_handle": "output",
            "target_handle": "input"
        }
    """
    source: str = Field(
        description="Source node ID"
    )
    target: str = Field(
        description="Target node ID"
    )
    source_handle: Optional[str] = Field(
        default=None,
        description="Source handle ID (for conditional nodes: true/false)"
    )
    target_handle: Optional[str] = Field(
        default=None,
        description="Target handle ID"
    )


class EdgeRemoveAction(BaseModel):
    """
    Action to remove an edge (connection) between nodes.

    Example:
        {
            "edge_id": "edge_123"
        }
    """
    edge_id: str = Field(
        description="ID of the edge to remove"
    )


class ConversationResponse(BaseModel):
    """
    Conversational response requiring no workflow changes.

    Used when agent needs to ask questions or provide information.

    Example:
        {
            "message": "Which database table contains customer data?",
            "needs_user_input": true,
            "context": "Found 3 tables: customers, orders, products"
        }
    """
    message: str = Field(
        description="Message to display to user"
    )
    needs_user_input: bool = Field(
        default=False,
        description="Whether agent is waiting for user response"
    )
    context: Optional[str] = Field(
        default=None,
        description="Additional context for the conversation"
    )


class WorkflowCompleteAction(BaseModel):
    """
    Signal that workflow building is complete.

    Example:
        {
            "summary": "Created workflow with 3 nodes: Database → Agent → Output"
        }
    """
    summary: str = Field(
        description="Summary of the completed workflow"
    )


class WorkflowBuilderResponse(BaseModel):
    """
    Structured response from supervisor agent.

    All agent responses must conform to this structure, enabling
    deterministic handling in the frontend.

    Example:
        {
            "action_type": "node_add",
            "data": {
                "node_type": "database",
                "position": {"x": 100, "y": 200},
                "config": {...}
            },
            "message": "Added database node to read customer data"
        }
    """
    action_type: Literal[
        "node_add",
        "node_edit",
        "node_remove",
        "edge_add",
        "edge_remove",
        "conversation",
        "workflow_complete"
    ] = Field(
        description="Type of action to take"
    )
    data: NodeAddAction | NodeEditAction | NodeRemoveAction | EdgeAddAction | EdgeRemoveAction | ConversationResponse | WorkflowCompleteAction = Field(
        description="Action-specific data"
    )
    message: str = Field(
        description="Human-readable explanation of the action"
    )


# ============================================================================
# Worker Agent Models
# ============================================================================

class WorkerToolResult(BaseModel):
    """
    Result from worker agent tool execution.

    Worker agent executes tools autonomously and returns results to supervisor.

    Example:
        {
            "success": true,
            "tool_name": "get_credentials",
            "result": [...],
            "summary": "Found 3 database credentials"
        }
    """
    success: bool = Field(
        description="Whether tool execution succeeded"
    )
    tool_name: str = Field(
        description="Name of the tool that was executed"
    )
    result: Any = Field(
        description="Tool execution result data"
    )
    summary: str = Field(
        description="Human-readable summary of the result"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if execution failed"
    )
