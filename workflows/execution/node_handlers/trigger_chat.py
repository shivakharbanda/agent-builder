"""
Chat Trigger Node Handler

Handles chat-triggered workflows - workflows started from user chat messages.
"""

import json
from datetime import datetime
from typing import Any, Dict
from workflows.execution.node_handlers.trigger_base import BaseTriggerNode


class ChatTriggerNode(BaseTriggerNode):
    """
    Chat trigger node implementation.

    This trigger type allows workflows to be started from user chat messages.
    The chat message is stored in WorkflowChatConversation and linked to the execution.

    Configuration Fields:
        welcome_message (str, required): Initial message shown to users
        context_instructions (str, optional): Instructions for processing chat input
        input_schema (str/dict, optional): Expected input format (JSON schema)

    Output:
        Returns structured data containing:
        - user_input: The chat message text
        - session_id: Chat session identifier
        - timestamp: When message was received
        - parsed_data: Structured data from message (if applicable)

    Note:
        The chat message is fetched from WorkflowChatConversation table
        using the execution_id to find the linked conversation.
    """

    node_type: str = 'trigger_chat'

    def validate(self) -> bool:
        """
        Validate chat trigger configuration.

        Checks:
        - Base trigger validation
        - welcome_message is present
        - input_schema is valid JSON (if provided)

        Returns:
            bool: True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Call parent validation
        super().validate()

        # Check required fields
        if 'welcome_message' not in self.configuration:
            raise ValueError("welcome_message is required for chat trigger")

        welcome_message = self.configuration['welcome_message']
        if not isinstance(welcome_message, str) or not welcome_message.strip():
            raise ValueError("welcome_message must be a non-empty string")

        # Validate context_instructions (if provided)
        if 'context_instructions' in self.configuration:
            instructions = self.configuration['context_instructions']
            if not isinstance(instructions, str):
                raise ValueError("context_instructions must be a string")

        # Validate input_schema (if provided)
        if 'input_schema' in self.configuration:
            schema = self.configuration['input_schema']

            # If it's a string, try to parse as JSON
            if isinstance(schema, str):
                if schema.strip():  # Not empty
                    try:
                        json.loads(schema)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"input_schema must be valid JSON: {str(e)}")

            # If it's a dict, it's already valid
            elif not isinstance(schema, dict):
                raise ValueError("input_schema must be a JSON string or dictionary")

        return True

    def execute(self, input_data: Any = None) -> Dict[str, Any]:
        """
        Execute chat trigger node.

        Fetches the chat conversation linked to this execution and returns
        the user message along with metadata.

        Args:
            input_data: Ignored (trigger nodes don't receive input)

        Returns:
            dict: Chat message data and metadata

        Raises:
            ValueError: If no chat conversation found for this execution
        """
        from workflows.models import WorkflowChatConversation, WorkflowExecution

        # Get the workflow execution to find linked chat conversation
        try:
            execution = WorkflowExecution.objects.get(id=self.execution_id)
        except WorkflowExecution.DoesNotExist:
            # If no execution_id or execution not found, return placeholder
            # This can happen during node testing/validation
            return self._get_placeholder_data()

        # Find chat conversation linked to this execution
        try:
            conversation = WorkflowChatConversation.objects.get(
                workflow_execution=execution
            )
        except WorkflowChatConversation.DoesNotExist:
            # No chat conversation found - this might be a test execution
            # Return placeholder data
            return self._get_placeholder_data()

        # Parse user message
        user_message = conversation.user_message

        # Try to extract structured data from message if input_schema is provided
        parsed_data = {}
        if 'input_schema' in self.configuration:
            # For now, just return the raw message
            # In future, could use NLP/LLM to extract structured data based on schema
            parsed_data = {'raw_message': user_message}

        # Build execution data
        execution_data = {
            'user_input': user_message,
            'session_id': str(conversation.session_id),
            'timestamp': conversation.created_at.isoformat(),
            'parsed_data': parsed_data,
            '_trigger': {
                'type': 'chat',
                'node_id': self.node_id,
                'workflow_id': self.workflow_id,
                'execution_id': self.execution_id,
                'conversation_id': conversation.id,
                'session_id': str(conversation.session_id),
                'welcome_message': self.configuration.get('welcome_message'),
                'description': self.configuration.get('description', 'Chat trigger')
            }
        }

        return execution_data

    def _get_placeholder_data(self) -> Dict[str, Any]:
        """
        Get placeholder data when no chat conversation is available.

        Used during testing/validation when node is executed without actual chat.

        Returns:
            dict: Placeholder execution data
        """
        return {
            'user_input': '[No chat message - test execution]',
            'session_id': '00000000-0000-0000-0000-000000000000',
            'timestamp': datetime.now().isoformat(),
            'parsed_data': {},
            '_trigger': {
                'type': 'chat',
                'node_id': self.node_id,
                'workflow_id': self.workflow_id,
                'execution_id': self.execution_id,
                'welcome_message': self.configuration.get('welcome_message'),
                'description': self.configuration.get('description', 'Chat trigger'),
                'is_placeholder': True
            }
        }

    def get_trigger_metadata(self) -> Dict[str, Any]:
        """Get chat trigger metadata."""
        return {
            **super().get_trigger_metadata(),
            'welcome_message': self.configuration.get('welcome_message'),
            'has_context_instructions': 'context_instructions' in self.configuration,
            'has_input_schema': 'input_schema' in self.configuration,
            'description': self.configuration.get('description', 'Chat-triggered workflow')
        }
