"""
Chat Trigger Node for Pydantic AI Graph

Handles chat-triggered workflows - workflows started from user chat messages.
"""

from datetime import datetime
from typing import Any, Dict, List
from pydantic_graph import GraphRunContext
from pydantic_ai.messages import ModelMessage, ModelMessagesTypeAdapter
from workflows.execution.graph_nodes.base import DynamicWorkflowNode
from workflows.execution.state import WorkflowState


class ChatTriggerNode(DynamicWorkflowNode):
    """
    Chat trigger node for Pydantic Graph execution.

    This is the starting node for chat-triggered workflows. It fetches the user's
    chat message from WorkflowChatConversation and initializes the workflow state.

    Configuration:
        welcome_message (str): Initial message shown to users
        context_instructions (str, optional): Instructions for processing chat input
        description (str, optional): Trigger description

    Output:
        Returns dict containing:
        - user_input: The chat message text
        - session_id: Chat session identifier
        - timestamp: When message was received
        - _trigger: Metadata about the trigger
    """

    async def execute(self, ctx: GraphRunContext[WorkflowState]) -> Dict[str, Any]:
        """
        Execute chat trigger - fetch chat message and initialize state.

        Args:
            ctx: Graph run context

        Returns:
            dict: Chat message data with metadata
        """
        from workflows.models import WorkflowChatConversation, WorkflowExecution

        # Get the workflow execution to find linked chat conversation (async ORM)
        try:
            execution = await WorkflowExecution.objects.aget(id=self.execution_id)
        except WorkflowExecution.DoesNotExist:
            # Return placeholder for testing
            return self._get_placeholder_data()

        # Find chat conversation linked to this execution (async ORM)
        try:
            conversation = await WorkflowChatConversation.objects.aget(
                workflow_execution=execution
            )
        except WorkflowChatConversation.DoesNotExist:
            # No chat conversation - return placeholder
            return self._get_placeholder_data()

        # Extract user message
        user_message = conversation.user_message

        # Fetch conversation history from previous messages in this session
        # Load message_history_blob from most recent completed conversation
        message_history: List[ModelMessage] = []

        # Get the most recent completed conversation in this session
        prev_conv = await WorkflowChatConversation.objects.filter(
            session_id=conversation.session_id,
            status='completed',  # Only include completed conversations
            created_at__lt=conversation.created_at  # Before current message
        ).order_by('-created_at').afirst()  # Get most recent

        if prev_conv and prev_conv.message_history_blob:
            try:
                # Deserialize message history from JSON blob
                message_history = ModelMessagesTypeAdapter.validate_json(prev_conv.message_history_blob)
                print(f"[CHAT TRIGGER NODE {self.node_id}] Loaded {len(message_history)} messages from history blob")
            except Exception as e:
                # CRITICAL ERROR - cannot deserialize message history
                # This indicates data corruption or serialization bug
                error_msg = f"Failed to deserialize message history from conversation {prev_conv.id}. This is a critical bug that needs immediate attention."
                print(f"[CHAT TRIGGER NODE {self.node_id}] ERROR: {error_msg}")
                print(f"[CHAT TRIGGER NODE {self.node_id}] Blob preview: {prev_conv.message_history_blob[:200]}")
                raise ValueError(error_msg) from e

        print(f"[CHAT TRIGGER NODE {self.node_id}] User message: {user_message[:100]}...")
        print(f"[CHAT TRIGGER NODE {self.node_id}] Message history: {len(message_history)} messages")

        # Build execution data (single object, not array)
        execution_data = {
            'user_input': user_message,
            'session_id': str(conversation.session_id),
            'timestamp': conversation.created_at.isoformat(),
            'message_history': message_history,  # List[ModelMessage] for agent
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

        Used during testing/validation.

        Returns:
            dict: Placeholder execution data
        """
        return {
            'user_input': '[No chat message - test execution]',
            'session_id': '00000000-0000-0000-0000-000000000000',
            'timestamp': datetime.now().isoformat(),
            '_trigger': {
                'type': 'chat',
                'node_id': self.node_id,
                'workflow_id': self.workflow_id,
                'execution_id': self.execution_id,
                'welcome_message': self.configuration.get('welcome_message', ''),
                'description': self.configuration.get('description', 'Chat trigger'),
                'is_placeholder': True
            }
        }
