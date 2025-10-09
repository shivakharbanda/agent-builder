"""
Base Trigger Node Class

This module contains the base class for all workflow trigger nodes.
Trigger nodes define how workflows are initiated (manual, schedule, chat, etc.).
"""

from typing import Any, Dict
from workflows.execution.node_handlers.base import BaseNode


class BaseTriggerNode(BaseNode):
    """
    Base class for all trigger nodes.

    Trigger nodes are special nodes that:
    - Must be the first node in a workflow
    - Cannot have incoming edges (source nodes only)
    - Generate/provide initial data for downstream nodes
    - Define how the workflow is initiated

    Attributes:
        category (str): Always 'trigger' for trigger nodes
    """

    category: str = 'trigger'

    def validate(self) -> bool:
        """
        Validate trigger node configuration.

        Base validation ensures:
        - Trigger nodes cannot receive input data
        - Configuration structure is valid

        Subclasses should call super().validate() and add their own validation.

        Returns:
            bool: True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Trigger nodes should not have input data (they are start nodes)
        # Note: This is checked during workflow validation, not here

        # Ensure configuration is a dict
        if not isinstance(self.configuration, dict):
            raise ValueError(f"Configuration must be a dictionary, got {type(self.configuration)}")

        return True

    def pre_execute(self, input_data: Any = None):
        """
        Pre-execution hook for trigger nodes.

        Trigger nodes should not receive input_data.
        We ignore input_data and set it to None.
        """
        self.input_data = None  # Trigger nodes don't use input
        super().pre_execute(None)

    def get_trigger_metadata(self) -> Dict[str, Any]:
        """
        Get trigger-specific metadata.

        Override in subclasses to provide trigger-specific information
        (e.g., cron schedule, chat session ID, etc.).

        Returns:
            dict: Trigger-specific metadata
        """
        return {
            'trigger_type': self.node_type,
            'description': self.configuration.get('description', '')
        }
