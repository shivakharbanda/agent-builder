"""
Agent Node for Pydantic AI Graph

Handles execution of AI agent nodes with tool support.
"""

import re
import asyncio
from typing import Any, Dict, Optional
from asgiref.sync import sync_to_async
from pydantic_graph import GraphRunContext, End
from workflows.execution.graph_nodes.base import DynamicWorkflowNode
from workflows.execution.state import WorkflowState
from agents.services.agent_executor import AgentExecutor
from agents.models import Agent, Prompt


class AgentNode(DynamicWorkflowNode):
    """
    AI Agent node for Pydantic Graph execution.

    Processes input data using configured AI agents with optional tool support.

    Configuration:
        agent_id (int): ID of AI agent to use
        llm_credential_id (int): ID of LLM credential
        model (str, optional): Model name override
        input_mapping (dict): Map placeholder names to input fields
        batch_size (int, optional): Batch size for processing
        timeout (int, optional): Timeout per batch

    Input:
        Receives data from previous node (trigger, database, etc.)

    Output:
        Returns processed data with agent outputs merged in
    """

    async def execute(self, ctx: GraphRunContext[WorkflowState]) -> Any:
        """
        Execute agent node - process data with AI agent.

        Args:
            ctx: Graph run context with state

        Returns:
            Processed data (list of dicts or single dict)
        """
        # Get configuration
        config = self.configuration
        agent_id = config.get('agent_id')
        llm_credential_id = config.get('llm_credential_id')
        model = config.get('model')
        input_mapping = config.get('input_mapping', {})

        if not agent_id:
            raise ValueError("agent_id is required")
        if not llm_credential_id:
            raise ValueError("llm_credential_id is required")

        # Check for toolbox connection
        toolbox_config = await self._get_toolbox_config(ctx)
        mcp_server_ids = None
        internal_tool_attachments = None

        if toolbox_config:
            mcp_server_ids = toolbox_config.get('mcp_server_ids')
            internal_tool_attachments = toolbox_config.get('internal_tool_attachments')
            print(f"[AGENT NODE {self.node_id}] Toolbox: {len(mcp_server_ids or [])} MCP, {len(internal_tool_attachments or [])} internal tools")

        # Get input data from state
        input_data = ctx.state.current_data

        if not input_data:
            print(f"[AGENT NODE {self.node_id}] No input data, returning empty result")
            return []

        # Detect input format
        is_trigger_data = isinstance(input_data, dict) and '_trigger' in input_data

        if is_trigger_data:
            # Trigger input - single object, wrap in array
            print(f"[AGENT NODE {self.node_id}] Processing trigger input")
            data_rows = [input_data]
        elif isinstance(input_data, list):
            # List of records
            print(f"[AGENT NODE {self.node_id}] Processing {len(input_data)} records")
            data_rows = input_data
        elif isinstance(input_data, dict):
            # Single dict - wrap in array
            print(f"[AGENT NODE {self.node_id}] Processing single record")
            data_rows = [input_data]
        else:
            print(f"[AGENT NODE {self.node_id}] Unexpected input type: {type(input_data)}")
            data_rows = []

        if not data_rows:
            return []

        # Load agent (async ORM)
        try:
            agent = await Agent.objects.aget(id=agent_id, is_active=True)
        except Agent.DoesNotExist:
            raise ValueError(f"Agent {agent_id} not found or inactive")

        # Create executor (AgentExecutor.__init__ does sync DB queries)
        executor = await sync_to_async(AgentExecutor)(agent_id=agent_id)

        # Process records
        results = []
        for record in data_rows:
            # Map inputs to placeholders
            agent_input = self._map_inputs(record, input_mapping)

            # Extract message history from record (if available from chat trigger)
            message_history = record.get('message_history', None)

            print(f"[AGENT NODE {self.node_id}] Agent input: {agent_input}")
            if message_history:
                print(f"[AGENT NODE {self.node_id}] Message history: {len(message_history)} messages")

            # Execute based on agent type
            if agent.return_type == 'structured':
                # Structured agent - returns JSON (wrap in async thread)
                result = await asyncio.to_thread(
                    executor.execute_structured,
                    placeholder_values=agent_input,
                    credential_id=int(llm_credential_id),
                    model=model if model else None,
                    mcp_server_ids=mcp_server_ids,
                    internal_tool_attachments=internal_tool_attachments
                )

                if result['success']:
                    # Merge agent output with original record
                    processed_record = {
                        **record,
                        **result['output'],  # Spread structured fields
                        '_agent_metadata': {
                            'execution_time_ms': result['execution_time_ms'],
                            'success': True,
                            'agent_type': 'structured'
                        }
                    }
                else:
                    processed_record = {
                        **record,
                        '_agent_metadata': {
                            'execution_time_ms': result['execution_time_ms'],
                            'success': False,
                            'error': result['error'],
                            'agent_type': 'structured'
                        }
                    }

            else:
                # Unstructured agent - returns text
                message = await self._prepare_unstructured_message(agent, agent_input)

                # Wrap in async thread
                result = await asyncio.to_thread(
                    executor.execute_unstructured,
                    message=message,
                    credential_id=int(llm_credential_id),
                    message_history=message_history,  # Pass ModelMessage list from trigger
                    model=model if model else None,
                    mcp_server_ids=mcp_server_ids,
                    internal_tool_attachments=internal_tool_attachments
                )

                if result['success']:
                    processed_record = {
                        **record,
                        'agent_response': result['response'],
                        'new_messages_json': result['new_messages_json'],  # Capture for persistence
                        '_agent_metadata': {
                            'execution_time_ms': result['execution_time_ms'],
                            'success': True,
                            'agent_type': 'unstructured'
                        }
                    }
                else:
                    processed_record = {
                        **record,
                        '_agent_metadata': {
                            'execution_time_ms': result['execution_time_ms'],
                            'success': False,
                            'error': result['error'],
                            'agent_type': 'unstructured'
                        }
                    }

            results.append(processed_record)

        print(f"[AGENT NODE {self.node_id}] Processed {len(results)} records")
        return results

    def _map_inputs(self, record: dict, input_mapping: dict) -> dict:
        """
        Map record fields to agent placeholder values.

        Args:
            record: Input record
            input_mapping: Dict of {placeholder: field_reference}

        Returns:
            dict: Mapped placeholder values
        """
        agent_input = {}

        for placeholder, column_ref in input_mapping.items():
            # column_ref format: "node_id.field_name" or "node_id.nested.path"
            # Remove node prefix
            if '.' in column_ref:
                parts = column_ref.split('.', 1)
                field_path = parts[1]
            else:
                field_path = column_ref

            # Navigate nested paths
            if '.' in field_path:
                value = record
                for part in field_path.split('.'):
                    if isinstance(value, dict) and part in value:
                        value = value[part]
                    else:
                        value = None
                        break
                agent_input[placeholder] = value
            else:
                # Simple field access
                agent_input[placeholder] = record.get(field_path)

        return agent_input

    async def _prepare_unstructured_message(self, agent: Agent, placeholder_values: dict) -> str:
        """
        Prepare message for unstructured agent by substituting placeholders.

        Args:
            agent: Agent instance
            placeholder_values: Values to substitute

        Returns:
            str: Message with placeholders substituted
        """
        # Get user prompt (async iteration)
        user_prompt_template = ""
        async for prompt in Prompt.objects.filter(agent=agent, is_active=True):
            if prompt.prompt_type == 'user':
                user_prompt_template = prompt.content
                break

        # Substitute {{placeholder}} with values
        def replace_placeholder(match):
            placeholder_name = match.group(1)
            return str(placeholder_values.get(placeholder_name, f"{{{{{placeholder_name}}}}}"))

        message = re.sub(r'\{\{(\w+)\}\}', replace_placeholder, user_prompt_template)
        return message

    async def _get_toolbox_config(self, ctx: GraphRunContext[WorkflowState]) -> Optional[Dict]:
        """
        Get toolbox configuration by finding and executing toolbox node.

        Looks for edges with targetHandle='tools-input' pointing to this node.

        Args:
            ctx: Graph run context

        Returns:
            dict or None: Toolbox configuration
        """
        # Find edges pointing to this node with tools-input handle
        toolbox_edges = [
            edge for edge in self.edges
            if edge.get('target') == self.node_id
            and edge.get('targetHandle') == 'tools-input'
        ]

        if not toolbox_edges:
            return None

        # Get toolbox node
        toolbox_edge = toolbox_edges[0]  # Should only be one
        toolbox_node_id = toolbox_edge.get('source')

        print(f"[AGENT NODE {self.node_id}] Found toolbox node: {toolbox_node_id}")

        # Get toolbox node instance from registry
        toolbox_node = self.node_registry.get(toolbox_node_id)
        if not toolbox_node:
            print(f"[AGENT NODE {self.node_id}] Toolbox node {toolbox_node_id} not in registry")
            return None

        # Execute toolbox node to get configuration
        toolbox_config = await toolbox_node.execute(ctx)
        return toolbox_config
