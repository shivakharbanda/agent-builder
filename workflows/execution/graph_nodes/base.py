"""
Base Dynamic Workflow Node for Pydantic AI Graph

This module defines the base class for all workflow nodes that run in Pydantic Graph.
All node types (trigger, agent, database, etc.) inherit from DynamicWorkflowNode.
"""

from dataclasses import dataclass
from typing import Any, Optional, Union, TYPE_CHECKING
from pydantic_graph import BaseNode, GraphRunContext, End
from workflows.execution.state import WorkflowState

if TYPE_CHECKING:
    from typing import Self


@dataclass
class DynamicWorkflowNode(BaseNode[WorkflowState]):
    """
    Base class for dynamically generated workflow nodes.

    This class provides the foundation for all Pydantic Graph nodes in the workflow system.
    Each node type (trigger, agent, database, etc.) inherits from this and implements execute().

    The key pattern:
    1. Node executes its logic in execute()
    2. Result is stored in state
    3. route_to_next() determines next node from edges
    4. Next node instance is returned (or End to finish)

    Attributes:
        node_id: Database ID of the WorkflowNode
        node_type: Type of node (trigger_chat, agent, database, etc.)
        configuration: Node configuration dict from database
        edges: List of workflow edges for routing
        node_registry: Dict mapping node_id -> node instance (for routing)
        workflow_id: ID of the workflow
        execution_id: ID of the WorkflowExecution
    """

    node_id: int
    node_type: str
    configuration: dict
    edges: list
    node_registry: dict  # node_id -> node instance
    workflow_id: int
    execution_id: int

    async def run(self, ctx: GraphRunContext[WorkflowState]) -> Union['DynamicWorkflowNode', End]:
        """
        Main execution entry point called by Pydantic Graph.

        This orchestrates the node execution:
        1. Track execution order
        2. Execute node-specific logic
        3. Store results in state
        4. Route to next node

        Args:
            ctx: Graph run context containing state and dependencies

        Returns:
            Next node instance to execute, or End to finish workflow
        """
        # Track execution order
        ctx.state.node_execution_order.append(self.node_id)

        print(f"\n[{self.node_type.upper()} NODE {self.node_id}] Starting execution")

        # Execute node-specific logic
        result = await self.execute(ctx)

        # Store result in state
        ctx.state.node_results[self.node_id] = result
        ctx.state.current_data = result

        print(f"[{self.node_type.upper()} NODE {self.node_id}] Execution completed")

        # Route to next node
        return self.route_to_next(ctx)

    async def execute(self, ctx: GraphRunContext[WorkflowState]) -> Any:
        """
        Execute the node's specific logic.

        Override this method in subclasses to implement node behavior.
        This is where the actual work happens (database queries, AI processing, etc.)

        Args:
            ctx: Graph run context containing state

        Returns:
            Output data from this node

        Raises:
            NotImplementedError: If subclass doesn't implement this
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement execute() method"
        )

    def route_to_next(self, ctx: GraphRunContext[WorkflowState]) -> Union['DynamicWorkflowNode', End]:
        """
        Determine next node based on edges.

        This is the default routing logic - find outgoing edge and return next node.
        Override this method for conditional routing (e.g., ConditionalNode).

        Args:
            ctx: Graph run context containing state

        Returns:
            Next node instance or End
        """
        next_node_id = self.get_next_node_id(ctx)

        if next_node_id is None:
            # No next node = end of workflow
            print(f"[{self.node_type.upper()} NODE {self.node_id}] Ending workflow")
            return End(ctx.state.current_data)

        # Return next node instance
        next_node = self.node_registry.get(next_node_id)
        if not next_node:
            raise ValueError(
                f"Next node {next_node_id} not found in registry. "
                f"Available nodes: {list(self.node_registry.keys())}"
            )

        print(f"[{self.node_type.upper()} NODE {self.node_id}] Routing to node {next_node_id} ({next_node.node_type})")
        return next_node

    def get_next_node_id(self, ctx: GraphRunContext[WorkflowState]) -> Optional[int]:
        """
        Get next node ID from edges.

        Override this for conditional routing (check sourceHandle, evaluate conditions, etc.)

        Args:
            ctx: Graph run context containing state

        Returns:
            Next node ID or None if workflow should end
        """
        # Find first edge from this node
        for edge in self.edges:
            if edge['source'] == self.node_id:
                return edge['target']

        return None

    def get_edges_from_node(self, source_handle: Optional[str] = None) -> list:
        """
        Helper to get all edges from this node, optionally filtered by sourceHandle.

        Args:
            source_handle: Filter edges by sourceHandle (e.g., 'true', 'false', 'data-input')

        Returns:
            List of matching edges
        """
        matching_edges = []
        for edge in self.edges:
            if edge['source'] == self.node_id:
                if source_handle is None:
                    matching_edges.append(edge)
                elif edge.get('sourceHandle') == source_handle:
                    matching_edges.append(edge)

        return matching_edges
