"""
Agent Executor Service

Handles dynamic agent execution using PydanticAI.
Loads agent configuration from database and executes with provided inputs.
"""

import os
import re
import time
from typing import Any, Dict, Optional, List
from datetime import datetime

from pydantic_ai import Agent as PydanticAgent, StructuredDict
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider
from pydantic_ai.providers.openai import OpenAIProvider

from agents.models import Agent, Prompt
from credentials.models import Credential


class AgentExecutionError(Exception):
    """Raised when agent execution fails"""
    pass


class AgentExecutor:
    """
    Service for executing AI agents dynamically from database configuration.

    Supports both structured and unstructured agent types.
    """

    def __init__(self, agent_id: int):
        """
        Initialize executor for a specific agent.

        Args:
            agent_id: ID of the agent to execute

        Raises:
            Agent.DoesNotExist: If agent not found
        """
        self.agent = Agent.objects.select_related('project').get(id=agent_id, is_active=True)
        self.prompts = list(Prompt.objects.filter(agent=self.agent, is_active=True))

    def _get_llm_model(self, credential_id: int, model: str = None):
        """
        Get PydanticAI model instance from credential.

        Args:
            credential_id: ID of LLM credential
            model: Optional model name override (e.g., 'gemini-1.5-flash', 'gpt-4o')

        Returns:
            PydanticAI model instance (OpenAIModel or GoogleModel)

        Raises:
            ValueError: If credential invalid or unsupported
        """
        try:
            credential = Credential.objects.select_related(
                'credential_type__category'
            ).get(id=credential_id, is_active=True, is_deleted=False)
        except Credential.DoesNotExist:
            raise ValueError(f"Credential {credential_id} not found or inactive")

        # Verify it's an LLM credential
        if credential.credential_type.category.name != 'LLM':
            raise ValueError("Credential must be of LLM category")

        # Get credential details
        raw_details = {d.field.field_name: d.value for d in credential.details.all()}

        # Normalize field names: lowercase, replace spaces with underscore
        # This handles fields like "API key" → "api_key", "API Key" → "api_key", etc.
        details = {
            k.lower().replace(' ', '_'): v
            for k, v in raw_details.items()
        }

        # Get credential type name to determine provider
        credential_type = credential.credential_type.type_name.lower()

        # Create appropriate model based on credential type
        if 'openai' in credential_type:
            api_key = details.get('api_key')
            # Use provided model or fallback to credential details or default
            model_name = model or details.get('model') or 'gpt-4o'
            if not api_key:
                raise ValueError(
                    f"OpenAI credential missing API key. Available fields: {list(raw_details.keys())}"
                )
            # Create provider with API key, then pass to model
            provider = OpenAIProvider(api_key=api_key)
            return OpenAIModel(model_name, provider=provider)

        elif 'gemini' in credential_type or 'google' in credential_type:
            api_key = details.get('api_key')
            # Use provided model or fallback to credential details or default
            model_name = model or details.get('model') or 'gemini-1.5-flash'
            if not api_key:
                raise ValueError(
                    f"Google/Gemini credential missing API key. Available fields: {list(raw_details.keys())}"
                )
            # Create provider with API key, then pass to model
            provider = GoogleProvider(api_key=api_key)
            return GoogleModel(model_name, provider=provider)

        else:
            raise ValueError(f"Unsupported LLM type: {credential_type}")

    def _substitute_placeholders(self, template: str, values: Dict[str, Any]) -> str:
        """
        Substitute {{placeholder}} values in template.

        Args:
            template: String with {{placeholder}} markers
            values: Dict mapping placeholder names to values

        Returns:
            String with placeholders replaced
        """
        def replace_fn(match):
            placeholder_name = match.group(1)
            return str(values.get(placeholder_name, f"{{{{{placeholder_name}}}}}"))

        return re.sub(r'\{\{(\w+)\}\}', replace_fn, template)

    def execute_structured(
        self,
        placeholder_values: Dict[str, Any],
        credential_id: int,
        model: str = None
    ) -> Dict[str, Any]:
        """
        Execute structured agent (returns JSON according to schema).

        Args:
            placeholder_values: Values for prompt placeholders
            credential_id: ID of LLM credential to use
            model: Optional model name override

        Returns:
            Dict containing:
                - success: bool
                - output: structured output from agent
                - execution_time_ms: execution time in milliseconds
                - error: error message if failed (optional)

        Raises:
            AgentExecutionError: If execution fails
        """
        start_time = time.time()

        try:
            # Validate agent is structured type
            if self.agent.return_type != 'structured':
                raise AgentExecutionError("Agent must be of type 'structured'")

            if not self.agent.schema_definition:
                raise AgentExecutionError("Structured agent missing schema_definition")

            # Get LLM model
            llm_model = self._get_llm_model(credential_id, model)

            # Build prompts with substituted values
            system_prompt = ""
            user_prompt = ""

            for prompt in self.prompts:
                content = self._substitute_placeholders(prompt.content, placeholder_values)
                if prompt.prompt_type == 'system':
                    system_prompt = content
                elif prompt.prompt_type == 'user':
                    user_prompt = content

            # DEBUG LOGGING
            print(f"\n{'='*80}")
            print(f"[AGENT EXECUTOR DEBUG] Agent: {self.agent.name} (ID: {self.agent.id})")
            print(f"[AGENT EXECUTOR DEBUG] Placeholder values: {placeholder_values}")
            print(f"[AGENT EXECUTOR DEBUG] System prompt (first 300 chars): {system_prompt[:300]}")
            print(f"[AGENT EXECUTOR DEBUG] User prompt (first 300 chars): {user_prompt[:300]}")
            print(f"{'='*80}\n")

            if not system_prompt or not user_prompt:
                raise AgentExecutionError("Agent must have both system and user prompts")

            # Create StructuredDict output type from schema
            output_type = StructuredDict(
                self.agent.schema_definition,
                name=f"{self.agent.name}Output",
                description=self.agent.description or f"Output schema for {self.agent.name}"
            )

            # Create PydanticAI agent
            pydantic_agent = PydanticAgent(
                model=llm_model,
                output_type=output_type,
                system_prompt=system_prompt
            )

            # Execute agent
            result = pydantic_agent.run_sync(user_prompt)

            execution_time_ms = int((time.time() - start_time) * 1000)

            return {
                'success': True,
                'output': result.output,
                'execution_time_ms': execution_time_ms
            }

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return {
                'success': False,
                'output': None,
                'execution_time_ms': execution_time_ms,
                'error': str(e)
            }

    def execute_unstructured(
        self,
        message: str,
        credential_id: int,
        conversation_history: Optional[List[Dict[str, str]]] = None,
        model: str = None
    ) -> Dict[str, Any]:
        """
        Execute unstructured agent (conversational, returns text).

        Args:
            message: User message
            credential_id: ID of LLM credential to use
            conversation_history: List of previous messages (optional)
                Format: [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]
            model: Optional model name override

        Returns:
            Dict containing:
                - success: bool
                - response: agent text response
                - conversation_history: updated conversation history
                - execution_time_ms: execution time in milliseconds
                - error: error message if failed (optional)
        """
        start_time = time.time()

        try:
            # Validate agent is unstructured type
            if self.agent.return_type != 'unstructured':
                raise AgentExecutionError("Agent must be of type 'unstructured'")

            # Get LLM model
            llm_model = self._get_llm_model(credential_id, model)

            # Get system prompt
            system_prompt = ""
            for prompt in self.prompts:
                if prompt.prompt_type == 'system':
                    system_prompt = prompt.content
                    break

            if not system_prompt:
                system_prompt = f"You are a helpful AI assistant named {self.agent.name}."

            # Create PydanticAI agent (no output_type for unstructured)
            pydantic_agent = PydanticAgent(
                model=llm_model,
                system_prompt=system_prompt
            )

            # Build message history for PydanticAI
            # Note: PydanticAI handles message history differently
            # For now, we'll concatenate history into the user message
            if conversation_history:
                # Build context from history
                context = "\n\nPrevious conversation:\n"
                for msg in conversation_history[-10:]:  # Last 10 messages
                    role = "User" if msg['role'] == 'user' else "Assistant"
                    context += f"{role}: {msg['content']}\n"
                full_message = context + f"\nUser: {message}"
            else:
                full_message = message

            # Execute agent
            result = pydantic_agent.run_sync(full_message)

            # Update conversation history
            updated_history = conversation_history or []
            updated_history.append({"role": "user", "content": message})
            updated_history.append({"role": "assistant", "content": result.output})

            execution_time_ms = int((time.time() - start_time) * 1000)

            return {
                'success': True,
                'response': result.output,
                'conversation_history': updated_history,
                'execution_time_ms': execution_time_ms
            }

        except Exception as e:
            execution_time_ms = int((time.time() - start_time) * 1000)
            return {
                'success': False,
                'response': None,
                'conversation_history': conversation_history or [],
                'execution_time_ms': execution_time_ms,
                'error': str(e)
            }

    def get_placeholders(self) -> List[str]:
        """
        Extract all unique placeholders from agent prompts.

        Returns:
            List of placeholder names
        """
        placeholders = set()

        for prompt in self.prompts:
            # Extract {{placeholder}} patterns
            matches = re.findall(r'\{\{(\w+)\}\}', prompt.content)
            placeholders.update(matches)

        return sorted(list(placeholders))
