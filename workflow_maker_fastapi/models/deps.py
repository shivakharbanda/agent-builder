"""
Dependency models for workflow builder agents.

These models define the dependencies (context) passed to agents during execution.
"""

from pydantic import BaseModel, Field
from typing import Optional, Any


class WorkflowConfig(BaseModel):
    """
    Current workflow configuration state.

    This represents the current state of the workflow being built/edited.
    """
    name: Optional[str] = Field(default=None, description="Workflow name")
    description: Optional[str] = Field(default=None, description="Workflow description")
    nodes: list[dict[str, Any]] = Field(default_factory=list, description="List of nodes")
    edges: list[dict[str, Any]] = Field(default_factory=list, description="List of edges")
    properties: Optional[dict[str, Any]] = Field(default=None, description="Workflow properties")


class SupervisorDeps(BaseModel):
    """
    Dependencies for supervisor agent.

    Includes session context and current workflow state for incremental building.
    """
    session_id: str = Field(
        description="Workflow builder session ID (maps to Django user/project)"
    )
    current_config: WorkflowConfig = Field(
        default_factory=WorkflowConfig,
        description="Current workflow configuration (for incremental/edit mode)"
    )

    @property
    def is_editing(self) -> bool:
        """Check if we're editing an existing workflow (has nodes)."""
        return len(self.current_config.nodes) > 0

    @property
    def is_new_workflow(self) -> bool:
        """Check if we're creating a new workflow (no nodes)."""
        return len(self.current_config.nodes) == 0

    def get_node_by_id(self, node_id: str) -> Optional[dict]:
        """Get node by ID from current config."""
        for node in self.current_config.nodes:
            if str(node.get('id')) == str(node_id):
                return node
        return None

    def get_next_node_position(self) -> dict[str, float]:
        """
        Calculate position for next node based on existing nodes.

        Returns position to the right of the rightmost node.
        """
        if not self.current_config.nodes:
            return {"x": 100, "y": 200}

        # Find rightmost node
        max_x = max(node.get('position', {}).get('x', 0) for node in self.current_config.nodes)
        return {"x": max_x + 300, "y": 200}


class WorkerDeps(BaseModel):
    """
    Dependencies for worker agent.

    Worker only needs session_id to execute tools.
    """
    session_id: str = Field(
        description="Workflow builder session ID"
    )
