"""
Workflow Graph Builder

Converts Django Workflow model into Pydantic AI Graph for execution.
"""

from typing import Dict, List, Optional, Union, get_args
from pydantic_graph import Graph, End
from workflows.models import Workflow, WorkflowNode
from workflows.execution.graph_nodes.base import DynamicWorkflowNode
from workflows.execution.graph_nodes.trigger_chat import ChatTriggerNode
from workflows.execution.graph_nodes.agent import AgentNode
from workflows.execution.graph_nodes.toolbox import ToolboxNode


class WorkflowGraphBuilder:
    """
    Builds Pydantic AI Graph from Django Workflow model.

    This class is responsible for converting the visual workflow JSON
    into a runnable Pydantic Graph with dynamic nodes.

    Usage:
        builder = WorkflowGraphBuilder(workflow)
        graph = builder.build()
        start_node = builder.get_start_node()
    """

    # Map node type string to node class
    NODE_CLASSES = {
        'trigger_chat': ChatTriggerNode,
        'trigger_manual': None,  # TODO: Implement
        'trigger_schedule': None,  # TODO: Implement
        'agent': AgentNode,
        'toolbox': ToolboxNode,
        'database': None,  # TODO: Implement
        'output': None,  # TODO: Implement
        'filter': None,  # TODO: Implement
        'script': None,  # TODO: Implement
        'conditional': None,  # TODO: Implement
        'internal_tool': None,  # TODO: Implement
    }

    def __init__(self, workflow: Workflow, execution_id: int = 0):
        """
        Initialize builder.

        Args:
            workflow: Workflow model instance
            execution_id: ID of WorkflowExecution (0 if not started yet)
        """
        self.workflow = workflow
        self.execution_id = execution_id
        self.config = workflow.configuration
        self.edges = self.config.get('edges', [])
        self.node_registry: Dict[int, DynamicWorkflowNode] = {}

    def build(self) -> Graph:
        """
        Build Pydantic Graph from workflow.

        Returns:
            Graph: Pydantic AI Graph ready for execution
        """
        print(f"\n[GRAPH BUILDER] Building graph for workflow {self.workflow.id}")

        # Get nodes from workflow configuration JSON
        nodes_config = self.config.get('nodes', [])

        print(f"[GRAPH BUILDER] Found {len(nodes_config)} nodes in configuration")

        # Create dynamic node instances
        graph_nodes = []
        for node_config in nodes_config:
            node_instance = self._create_node_from_config(node_config)
            if node_instance:
                node_id = node_config['id']
                node_type = node_config['type']

                # Always add to registry (for lookups by other nodes)
                self.node_registry[node_id] = node_instance

                # Only add to graph if it's an execution node (exclude toolbox)
                # Toolbox is a configuration provider, not part of execution flow
                if node_type != 'toolbox':
                    graph_nodes.append(node_instance)
                    print(f"[GRAPH BUILDER] Created execution node: {node_id} ({node_type})")
                else:
                    print(f"[GRAPH BUILDER] Created config node (not in graph): {node_id} ({node_type})")

        if not graph_nodes:
            raise ValueError("No valid nodes found in workflow")

        # Build dynamic return type annotation
        # Pydantic Graph requires Union of concrete node types, not base class
        # Dynamically construct Union[AgentNode | ChatTriggerNode | ... | End]
        print(f"[GRAPH BUILDER] Building dynamic return type annotations")

        node_type_set = set(type(node) for node in graph_nodes)
        node_types = tuple(node_type_set)

        # Create Union type with all node types + End
        DynamicReturnType = Union[node_types + (End,)]

        print(f"[GRAPH BUILDER] Return type: {DynamicReturnType}")

        # Inject return type into each node's run() method
        for node in graph_nodes:
            node.run.__annotations__['return'] = DynamicReturnType
            print(f"[GRAPH BUILDER] Injected return type for {type(node).__name__}")

        # Build graph
        print(f"[GRAPH BUILDER] Building graph with {len(graph_nodes)} nodes")
        graph = Graph(nodes=tuple(graph_nodes))

        print(f"[GRAPH BUILDER] Graph built successfully")
        return graph

    def _create_node_from_config(self, node_config: dict) -> Optional[DynamicWorkflowNode]:
        """
        Create dynamic node instance from configuration JSON.

        Args:
            node_config: Node configuration dict from workflow.configuration['nodes']

        Returns:
            DynamicWorkflowNode instance or None if node type not implemented
        """
        node_type = node_config.get('type')
        node_id = node_config.get('id')
        config = node_config.get('config', {})

        node_class = self.NODE_CLASSES.get(node_type)

        if not node_class:
            print(f"[GRAPH BUILDER] WARNING: Node type '{node_type}' not implemented yet")
            return None

        # Create node instance
        node = node_class(
            node_id=node_id,
            node_type=node_type,
            configuration=config,
            edges=self.edges,
            node_registry=self.node_registry,  # Shared registry for routing
            workflow_id=self.workflow.id,
            execution_id=self.execution_id
        )

        return node

    def get_start_node(self) -> Optional[DynamicWorkflowNode]:
        """
        Get the starting node for execution.

        Looks for trigger nodes first, then falls back to first node.

        Returns:
            DynamicWorkflowNode: Starting node or None
        """
        # Look for trigger nodes
        trigger_types = ['trigger_manual', 'trigger_chat', 'trigger_schedule']

        for node in self.node_registry.values():
            if node.node_type in trigger_types:
                print(f"[GRAPH BUILDER] Start node: {node.node_id} ({node.node_type})")
                return node

        # Fallback to first node by position
        if self.node_registry:
            first_node = list(self.node_registry.values())[0]
            print(f"[GRAPH BUILDER] Start node (fallback): {first_node.node_id} ({first_node.node_type})")
            return first_node

        print(f"[GRAPH BUILDER] WARNING: No start node found")
        return None

    def update_execution_id(self, execution_id: int):
        """
        Update execution_id for all nodes.

        Called when execution starts to set the actual execution ID.

        Args:
            execution_id: ID of WorkflowExecution
        """
        self.execution_id = execution_id
        for node in self.node_registry.values():
            node.execution_id = execution_id

    def get_node(self, node_id: int) -> Optional[DynamicWorkflowNode]:
        """
        Get node by ID.

        Args:
            node_id: Node database ID

        Returns:
            DynamicWorkflowNode or None
        """
        return self.node_registry.get(node_id)

    def get_edges_for_node(self, node_id: int) -> List[dict]:
        """
        Get all edges from a node.

        Args:
            node_id: Source node ID

        Returns:
            list: List of edge dicts
        """
        return [edge for edge in self.edges if edge.get('source') == node_id]

    def visualize(self) -> str:
        """
        Generate Mermaid diagram of workflow.

        Returns:
            str: Mermaid diagram code
        """
        lines = ["stateDiagram-v2"]

        # Add nodes
        for node_id, node in self.node_registry.items():
            lines.append(f"    {node_id}: {node.node_type}")

        # Add edges
        for edge in self.edges:
            source = edge.get('source')
            target = edge.get('target')
            handle = edge.get('targetHandle', '')

            if handle:
                lines.append(f"    {source} --> {target}: {handle}")
            else:
                lines.append(f"    {source} --> {target}")

        return "\n".join(lines)
