"""
Conversation Manager

Utility for managing conversation history in unstructured agent testing.
"""

from typing import List, Dict, Any, Optional


class ConversationManager:
    """
    Manages conversation history for unstructured agents.

    Provides utilities for validating, limiting, and formatting conversation history.
    """

    MAX_HISTORY_LENGTH = 50  # Maximum messages to store
    DEFAULT_CONTEXT_WINDOW = 10  # Messages to include in context

    @staticmethod
    def validate_history(conversation_history: Optional[List[Dict[str, str]]]) -> List[Dict[str, str]]:
        """
        Validate and clean conversation history.

        Args:
            conversation_history: List of conversation messages

        Returns:
            Validated and cleaned conversation history

        Raises:
            ValueError: If history format is invalid
        """
        if conversation_history is None:
            return []

        if not isinstance(conversation_history, list):
            raise ValueError("conversation_history must be a list")

        validated = []
        for msg in conversation_history:
            if not isinstance(msg, dict):
                raise ValueError("Each message must be a dictionary")

            if 'role' not in msg or 'content' not in msg:
                raise ValueError("Each message must have 'role' and 'content' keys")

            if msg['role'] not in ['user', 'assistant']:
                raise ValueError(f"Invalid role: {msg['role']}. Must be 'user' or 'assistant'")

            validated.append({
                'role': msg['role'],
                'content': str(msg['content'])
            })

        return validated

    @staticmethod
    def limit_history(
        conversation_history: List[Dict[str, str]],
        max_length: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Limit conversation history to maximum length.

        Keeps most recent messages within the limit.

        Args:
            conversation_history: Full conversation history
            max_length: Maximum messages to keep (default: MAX_HISTORY_LENGTH)

        Returns:
            Truncated conversation history
        """
        if max_length is None:
            max_length = ConversationManager.MAX_HISTORY_LENGTH

        if len(conversation_history) <= max_length:
            return conversation_history

        return conversation_history[-max_length:]

    @staticmethod
    def get_context_window(
        conversation_history: List[Dict[str, str]],
        window_size: Optional[int] = None
    ) -> List[Dict[str, str]]:
        """
        Get recent messages for context window.

        Args:
            conversation_history: Full conversation history
            window_size: Number of recent messages to include (default: DEFAULT_CONTEXT_WINDOW)

        Returns:
            Recent messages for context
        """
        if window_size is None:
            window_size = ConversationManager.DEFAULT_CONTEXT_WINDOW

        return conversation_history[-window_size:]

    @staticmethod
    def format_for_display(conversation_history: List[Dict[str, str]]) -> str:
        """
        Format conversation history as human-readable text.

        Args:
            conversation_history: Conversation messages

        Returns:
            Formatted conversation as string
        """
        if not conversation_history:
            return "No conversation history"

        lines = []
        for msg in conversation_history:
            role = "User" if msg['role'] == 'user' else "Assistant"
            lines.append(f"{role}: {msg['content']}")

        return "\n\n".join(lines)

    @staticmethod
    def count_tokens_estimate(conversation_history: List[Dict[str, str]]) -> int:
        """
        Estimate token count for conversation history.

        Uses simple heuristic: ~4 characters per token.

        Args:
            conversation_history: Conversation messages

        Returns:
            Estimated token count
        """
        total_chars = sum(len(msg['content']) for msg in conversation_history)
        return total_chars // 4

    @staticmethod
    def clear_history() -> List[Dict[str, str]]:
        """
        Return empty conversation history.

        Returns:
            Empty list
        """
        return []

    @staticmethod
    def messages_to_history(messages: List[Any]) -> List[Dict[str, str]]:
        """
        Convert PydanticAI ModelMessage objects to frontend conversation format.

        Args:
            messages: List of PydanticAI ModelMessage objects

        Returns:
            List of conversation messages with 'role' and 'content' keys
        """
        from pydantic_ai.messages import ModelRequest, ModelResponse, UserPromptPart, TextPart

        conversation = []

        for msg in messages:
            if isinstance(msg, ModelRequest):
                # Iterate through all parts to find UserPromptPart
                # (first part might be SystemPromptPart)
                for part in msg.parts:
                    if isinstance(part, UserPromptPart):
                        conversation.append({
                            'role': 'user',
                            'content': part.content
                        })

            elif isinstance(msg, ModelResponse):
                # Iterate through all parts to find TextPart
                for part in msg.parts:
                    if isinstance(part, TextPart):
                        conversation.append({
                            'role': 'assistant',
                            'content': part.content
                        })

        return conversation
