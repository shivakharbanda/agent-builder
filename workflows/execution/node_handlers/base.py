"""
Base Node Class

This module contains the abstract base class for all workflow nodes.
All node handlers must inherit from BaseNode and implement the required methods.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from datetime import datetime


class BaseNode(ABC):
    """
    Abstract base class for all workflow nodes.

    Defines the interface and common functionality that all node handlers must implement.
    Each node type (database, agent, output, etc.) should inherit from this class.

    Attributes:
        node_id (int): Database ID of the node
        node_type (str): Type of node (database, agent, output, etc.)
        workflow_id (int): ID of the parent workflow
        execution_id (int): ID of the current workflow execution
        position (int): Position/order of node in workflow
        configuration (dict): Node configuration from database
        input_data: Data received from previous node
        output_data: Data produced by this node
        status (str): Current execution status (pending, running, completed, failed)
        started_at (datetime): When node execution started
        completed_at (datetime): When node execution completed
        execution_time (float): Total execution time in seconds
        error_message (str): Error message if execution failed
    """

    # Class-level attributes (override in subclasses)
    node_type: str = None
    category: str = None

    def __init__(
        self,
        node_id: int,
        node_type: str,
        configuration: Dict[str, Any],
        workflow_id: int,
        execution_id: int,
        position: int = 0
    ):
        """
        Initialize the node.

        Args:
            node_id: Database ID of the node
            node_type: Type of node (database, agent, etc.)
            configuration: Node configuration dictionary
            workflow_id: ID of parent workflow
            execution_id: ID of current execution
            position: Position in workflow execution order
        """
        # Node identification
        self.node_id = node_id
        self.node_type = node_type
        self.workflow_id = workflow_id
        self.execution_id = execution_id
        self.position = position

        # Configuration
        self.configuration = configuration

        # Input/Output
        self.input_data: Any = None
        self.output_data: Any = None

        # Execution state
        self.status: str = 'pending'
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.execution_time: Optional[float] = None
        self.error_message: Optional[str] = None

        # Dependencies (override in subclasses)
        self.required_dependencies: List[str] = []
        self.optional_dependencies: List[str] = []

    @abstractmethod
    def validate(self) -> bool:
        """
        Validate node configuration.

        This method should check that all required configuration fields are present
        and valid. Should raise ValueError if configuration is invalid.

        Returns:
            bool: True if configuration is valid

        Raises:
            ValueError: If configuration is invalid with description of error
        """
        pass

    @abstractmethod
    def execute(self, input_data: Any = None) -> Any:
        """
        Execute the node's main logic.

        This is where the actual work happens - database queries, AI processing,
        data filtering, etc. Must be implemented by each node type.

        Args:
            input_data: Data from previous node (if any)

        Returns:
            Any: Processed output data to pass to next node

        Raises:
            Exception: Any errors during execution
        """
        pass

    def pre_execute(self, input_data: Any = None):
        """
        Hook called before execute().

        Sets up execution state, stores input data, records start time.
        Can be overridden by subclasses for custom pre-processing.

        Args:
            input_data: Data from previous node
        """
        self.input_data = input_data
        self.status = 'running'
        self.started_at = datetime.now()

    def post_execute(self):
        """
        Hook called after successful execute().

        Updates execution state, records completion time and duration.
        Can be overridden by subclasses for custom post-processing.
        """
        self.status = 'completed'
        self.completed_at = datetime.now()

        if self.started_at:
            duration = self.completed_at - self.started_at
            self.execution_time = duration.total_seconds()

    def run(self, input_data: Any = None) -> Any:
        """
        Main execution wrapper with error handling.

        Orchestrates the execution flow:
        1. Validates configuration
        2. Calls pre_execute() hook
        3. Calls execute() with input data
        4. Calls post_execute() hook
        5. Returns output data

        Handles errors and updates execution state accordingly.

        Args:
            input_data: Data from previous node

        Returns:
            Any: Output data from execute()

        Raises:
            Exception: Re-raises any exceptions from execute() after updating state
        """
        try:
            # Validate configuration first
            self.validate()

            # Execute node
            self.pre_execute(input_data)
            self.output_data = self.execute(input_data)
            self.post_execute()

            return self.output_data

        except Exception as e:
            # Update status on failure
            self.status = 'failed'
            self.error_message = str(e)
            self.completed_at = datetime.now()

            if self.started_at:
                duration = self.completed_at - self.started_at
                self.execution_time = duration.total_seconds()

            # Re-raise exception for workflow handler to handle
            raise

    def get_metadata(self) -> Dict[str, Any]:
        """
        Get execution metadata for logging/tracking.

        Returns:
            dict: Metadata about node execution including status, timing, errors
        """
        return {
            'node_id': self.node_id,
            'node_type': self.node_type,
            'position': self.position,
            'status': self.status,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'execution_time': self.execution_time,
            'error_message': self.error_message,
            'input_size': len(self.input_data) if isinstance(self.input_data, (list, dict, str)) else None,
            'output_size': len(self.output_data) if isinstance(self.output_data, (list, dict, str)) else None,
        }

    def check_dependencies(self) -> bool:
        """
        Check if all required dependencies are available.

        Override in subclasses to check for specific dependencies like
        database connections, API credentials, etc.

        Returns:
            bool: True if all dependencies are available
        """
        return True

    def __repr__(self) -> str:
        """String representation of node."""
        return f"<{self.__class__.__name__}(id={self.node_id}, type={self.node_type}, status={self.status})>"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.__class__.__name__} #{self.node_id} ({self.status})"
