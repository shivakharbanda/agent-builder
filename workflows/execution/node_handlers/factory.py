"""
Node Factory

This module contains the NodeFactory class responsible for creating
appropriate node handler instances based on node type.
"""

from typing import Dict, Any
from .base import BaseNode


class NodeFactory:
    """
    Factory class for creating node handler instances.

    Uses the Factory Pattern to instantiate the correct node handler class
    based on node type. Maintains a registry of available node types.

    Usage:
        node = NodeFactory.create_node(
            node_id=1,
            node_type='database',
            configuration={...},
            workflow_id=5,
            execution_id=10
        )
        result = node.run(input_data)
    """

    # Registry mapping node_type string to handler class
    # Will be populated when node handler classes are imported
    NODE_REGISTRY: Dict[str, type] = {}

    @classmethod
    def register_node_types(cls):
        """
        Register all node handler classes.

        This method imports and registers all node handlers.
        Called automatically when module is imported.
        """
        # Import here to avoid circular imports
        from .database import DatabaseNode
        from .agent import AgentNode
        from .output import OutputNode
        from .filter import FilterNode
        from .script import ScriptNode
        from .conditional import ConditionalNode

        cls.NODE_REGISTRY = {
            'database': DatabaseNode,
            'agent': AgentNode,
            'output': OutputNode,
            'filter': FilterNode,
            'script': ScriptNode,
            'conditional': ConditionalNode,
        }

    @classmethod
    def create_node(
        cls,
        node_id: int,
        node_type: str,
        configuration: Dict[str, Any],
        workflow_id: int,
        execution_id: int,
        position: int = 0
    ) -> BaseNode:
        """
        Create a node handler instance based on node type.

        Factory method that instantiates the appropriate node handler class
        for the given node type.

        Args:
            node_id: Database ID of the node
            node_type: Type of node (database, agent, output, filter, script, conditional)
            configuration: Node configuration dictionary
            workflow_id: ID of parent workflow
            execution_id: ID of current execution
            position: Position in workflow execution order (default: 0)

        Returns:
            BaseNode: Instance of appropriate node handler class

        Raises:
            ValueError: If node_type is not registered in NODE_REGISTRY
        """
        # Ensure registry is populated
        if not cls.NODE_REGISTRY:
            cls.register_node_types()

        # Get handler class from registry
        node_class = cls.NODE_REGISTRY.get(node_type)

        if not node_class:
            available = ', '.join(cls.NODE_REGISTRY.keys())
            raise ValueError(
                f"Unknown node type: '{node_type}'. "
                f"Available types: {available}"
            )

        # Instantiate and return node handler
        return node_class(
            node_id=node_id,
            node_type=node_type,
            configuration=configuration,
            workflow_id=workflow_id,
            execution_id=execution_id,
            position=position
        )

    @classmethod
    def get_available_node_types(cls) -> list:
        """
        Get list of registered node types.

        Returns:
            list: List of available node type strings
        """
        if not cls.NODE_REGISTRY:
            cls.register_node_types()

        return list(cls.NODE_REGISTRY.keys())

    @classmethod
    def register_custom_node_type(cls, node_type: str, node_class: type):
        """
        Register a custom/plugin node type.

        Allows extending the system with custom node types without
        modifying core code.

        Args:
            node_type: String identifier for the node type
            node_class: Class that inherits from BaseNode

        Raises:
            ValueError: If node_class doesn't inherit from BaseNode
        """
        if not issubclass(node_class, BaseNode):
            raise ValueError(
                f"Node class {node_class.__name__} must inherit from BaseNode"
            )

        cls.NODE_REGISTRY[node_type] = node_class

    @classmethod
    def is_registered(cls, node_type: str) -> bool:
        """
        Check if a node type is registered.

        Args:
            node_type: Node type string to check

        Returns:
            bool: True if node type is registered
        """
        if not cls.NODE_REGISTRY:
            cls.register_node_types()

        return node_type in cls.NODE_REGISTRY


# Auto-register node types on module import
NodeFactory.register_node_types()
