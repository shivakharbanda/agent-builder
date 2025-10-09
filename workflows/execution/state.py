"""
Workflow State for Pydantic AI Graph Execution

This module defines the state object that flows through the Pydantic Graph
during workflow execution. The state is mutated by nodes as they execute.
"""

from pydantic import BaseModel, Field
from typing import Any, Dict, List, Optional


class WorkflowState(BaseModel):
    """
    State that flows through Pydantic Graph execution.

    This state object is passed to each node and can be mutated during execution.
    It tracks the current data being processed, execution history, and metadata.

    Attributes:
        workflow_id: ID of the workflow being executed
        execution_id: ID of the WorkflowExecution record
        current_data: Current data being processed (flows between nodes)
        context_data: Reference data (not iterated, just referenced)
        node_results: History of outputs from each node {node_id: output}
        node_execution_order: List of node IDs in execution order
        variables: Workflow-level variables for sharing state
        metadata: Additional metadata for tracking
    """

    # Core identifiers
    workflow_id: int
    execution_id: int

    # Data pipeline
    current_data: Any = None
    context_data: Dict[str, Any] = Field(default_factory=dict)

    # Execution tracking
    node_results: Dict[int, Any] = Field(default_factory=dict)
    node_execution_order: List[int] = Field(default_factory=list)

    # Workflow variables (for sharing state across nodes)
    variables: Dict[str, Any] = Field(default_factory=dict)

    # Metadata
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        # Allow arbitrary types (Django models, etc.)
        arbitrary_types_allowed = True
