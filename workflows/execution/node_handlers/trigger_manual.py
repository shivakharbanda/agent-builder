"""
Manual Trigger Node Handler

Handles manual workflow triggers - workflows started via button click or API call.
"""

import json
from typing import Any, Dict
from workflows.execution.node_handlers.trigger_base import BaseTriggerNode


class ManualTriggerNode(BaseTriggerNode):
    """
    Manual trigger node implementation.

    This trigger type allows workflows to be started manually by:
    - Clicking "Run Workflow" button in UI
    - Making API call to /api/workflows/{id}/execute/
    - Direct execution from workflow detail page

    Configuration Fields:
        description (str, optional): Human-readable description of when to run this workflow
        initial_data (str/dict, optional): JSON data to pass to downstream nodes

    Output:
        Returns initial_data (if provided) or empty dict to downstream nodes
    """

    node_type: str = 'trigger_manual'

    def validate(self) -> bool:
        """
        Validate manual trigger configuration.

        Checks:
        - Base trigger validation
        - initial_data is valid JSON (if provided)

        Returns:
            bool: True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Call parent validation
        super().validate()

        # Validate initial_data if provided
        if 'initial_data' in self.configuration:
            initial_data = self.configuration['initial_data']

            # If it's a string, try to parse as JSON
            if isinstance(initial_data, str):
                if initial_data.strip():  # Not empty
                    try:
                        json.loads(initial_data)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"initial_data must be valid JSON: {str(e)}")

            # If it's a dict, it's already valid
            elif not isinstance(initial_data, dict):
                raise ValueError("initial_data must be a JSON string or dictionary")

        return True

    def execute(self, input_data: Any = None) -> Dict[str, Any]:
        """
        Execute manual trigger node.

        Returns initial_data (if configured) or metadata about the manual trigger.

        Args:
            input_data: Ignored (trigger nodes don't receive input)

        Returns:
            dict: Initial data for workflow or execution metadata
        """
        # Get initial_data from configuration
        initial_data = self.configuration.get('initial_data')

        if initial_data:
            # Parse JSON string if needed
            if isinstance(initial_data, str) and initial_data.strip():
                try:
                    parsed_data = json.loads(initial_data)
                except json.JSONDecodeError:
                    # If parsing fails, wrap in a dict
                    parsed_data = {'data': initial_data}
            elif isinstance(initial_data, dict):
                parsed_data = initial_data
            else:
                parsed_data = {}
        else:
            # No initial data provided
            parsed_data = {}

        # Add trigger metadata
        trigger_metadata = {
            '_trigger': {
                'type': 'manual',
                'node_id': self.node_id,
                'workflow_id': self.workflow_id,
                'execution_id': self.execution_id,
                'description': self.configuration.get('description', 'Manual trigger')
            }
        }

        # Merge trigger metadata with initial data
        # If parsed_data is a list, wrap it
        if isinstance(parsed_data, list):
            return {
                'data': parsed_data,
                **trigger_metadata
            }
        else:
            return {
                **parsed_data,
                **trigger_metadata
            }

    def get_trigger_metadata(self) -> Dict[str, Any]:
        """Get manual trigger metadata."""
        return {
            **super().get_trigger_metadata(),
            'has_initial_data': 'initial_data' in self.configuration,
            'description': self.configuration.get('description', 'Manual workflow trigger')
        }
