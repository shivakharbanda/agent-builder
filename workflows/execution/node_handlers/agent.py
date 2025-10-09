"""
Agent Node Handler

Handles execution of AI agent nodes.
Processes data using configured AI agents.
"""

from typing import Any
import re
from .base import BaseNode
from agents.services.agent_executor import AgentExecutor
from agents.models import Agent, Prompt


class AgentNode(BaseNode):
    """
    AI Agent node handler.

    Processes input data using configured AI agents.
    Supports batch processing and input field mapping.

    Configuration Required:
        - agent_id (int): ID of AI agent to use
        - batch_size (int, optional): Number of records per batch (default: 100)
        - timeout (int, optional): Timeout per batch in seconds (default: 30)
        - input_mapping (dict, optional): Field mappings for agent inputs

    Inputs:
        Data to be processed by the agent (typically array of objects)

    Outputs:
        Processed results from agent (structure depends on agent return type)
    """

    node_type = 'agent'
    category = 'processor'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Define dependencies
        self.required_dependencies = ['agent_id', 'llm_credential_id']
        self.optional_dependencies = ['batch_size', 'timeout', 'input_mapping', 'model']

    def validate(self) -> bool:
        """
        Validate agent node configuration.

        Checks:
        - agent_id is present and valid
        - llm_credential_id is present and valid
        - LLM credential is of correct category
        - batch_size is within limits (1-1000)
        - timeout is within limits (5-300)

        Returns:
            bool: True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        from credentials.models import Credential

        config = self.configuration

        # Check agent_id is provided
        if not config.get('agent_id'):
            raise ValueError("agent_id is required")

        # Check llm_credential_id is provided
        llm_credential_id = config.get('llm_credential_id')
        if not llm_credential_id:
            raise ValueError("llm_credential_id is required")

        # Verify LLM credential exists and is active
        try:
            credential = Credential.objects.get(
                id=llm_credential_id,
                is_active=True,
                is_deleted=False
            )
        except Credential.DoesNotExist:
            raise ValueError(f"LLM Credential with ID {llm_credential_id} not found or inactive")

        # Verify credential is LLM type
        category_name = credential.credential_type.category.name
        if category_name != 'LLM':
            raise ValueError(
                f"Credential must be LLM type, got '{category_name}'. "
                f"Agent node requires LLM credentials (OpenAI, Gemini, etc.)."
            )

        # Validate batch_size if provided
        batch_size = config.get('batch_size')
        if batch_size is not None and batch_size != '':
            try:
                batch_size = int(batch_size)
                if not (1 <= batch_size <= 1000):
                    raise ValueError("batch_size must be between 1 and 1000")
            except (ValueError, TypeError) as e:
                if "invalid literal" in str(e):
                    raise ValueError("batch_size must be a valid integer")
                raise

        # Validate timeout if provided
        timeout = config.get('timeout')
        if timeout is not None and timeout != '':
            try:
                timeout = int(timeout)
                if not (5 <= timeout <= 300):
                    raise ValueError("timeout must be between 5 and 300 seconds")
            except (ValueError, TypeError) as e:
                if "invalid literal" in str(e):
                    raise ValueError("timeout must be a valid integer")
                raise

        return True

    def execute(self, input_data: Any = None) -> Any:
        """
        Process data using AI agent with batching and input mapping.

        Args:
            input_data: Data to be processed (typically list of dicts from database node)

        Returns:
            List[Dict]: Processed results from agent with original data + agent outputs

        Flow:
            1. Check for toolbox connection (bottom handle)
            2. Validate input is list of dicts
            3. Apply input_mapping to transform data
            4. Split into batches based on batch_size
            5. Process each batch with tools from toolbox (if connected)
            6. Aggregate and return results
        """
        from datetime import datetime
        import time

        config = self.configuration

        # Check for toolbox connection (bottom handle = "tools-input")
        mcp_server_ids = None
        internal_tool_attachments = None

        toolbox_config = self._get_toolbox_config()
        if toolbox_config:
            mcp_server_ids = toolbox_config.get('mcp_server_ids')
            internal_tool_attachments = toolbox_config.get('internal_tool_attachments')
            print(f"[AGENT NODE] Toolbox connected: {len(mcp_server_ids or [])} MCP servers, {len(internal_tool_attachments or [])} internal tools")

        # Get configuration with defaults (convert strings to int)
        batch_size = config.get('batch_size', 100)
        if isinstance(batch_size, str) and batch_size:
            batch_size = int(batch_size)
        elif not batch_size:
            batch_size = 100

        timeout = config.get('timeout', 30)
        if isinstance(timeout, str) and timeout:
            timeout = int(timeout)
        elif not timeout:
            timeout = 30

        input_mapping = config.get('input_mapping', {})

        # Validate input data
        if not input_data:
            return []

        # Detect input data format
        # Check if input is from trigger (has _trigger metadata)
        is_trigger_data = isinstance(input_data, dict) and '_trigger' in input_data

        if is_trigger_data:
            # Trigger nodes return single objects - wrap in array for uniform processing
            trigger_type = input_data.get('_trigger', {}).get('type', 'unknown')
            print(f"\n[AGENT NODE DEBUG] Trigger input detected: {trigger_type}")
            print(f"  - Available fields: {list(input_data.keys())}")
            data_rows = [input_data]  # Wrap single object as 1-row array
            context_row = {}
        elif isinstance(input_data, dict) and 'data' in input_data:
            # Structured format from database: {'data': [...], 'context': {...}}
            data_rows = input_data.get('data', [])
            context_row = input_data.get('context', {})
            print(f"\n[AGENT NODE DEBUG] Received structured input:")
            print(f"  - data rows: {len(data_rows)}")
            print(f"  - context keys: {list(context_row.keys())}")
            print(f"  - context: {context_row}")
        else:
            # Backward compatibility: treat as data rows
            if isinstance(input_data, list):
                data_rows = input_data
            else:
                data_rows = []
            context_row = {}
            print(f"\n[AGENT NODE DEBUG] Received legacy format: {len(data_rows) if data_rows else 0} rows")

        # If no records, return empty
        if not data_rows or len(data_rows) == 0:
            return []

        # Merge context into each data row BEFORE mapping
        merged_data = []
        for record in data_rows:
            # Merge context columns into this row
            merged_record = {**record, **context_row}
            merged_data.append(merged_record)

        print(f"[AGENT NODE DEBUG] After merging context, sample merged record keys: {list(merged_data[0].keys()) if merged_data else []}")

        # Apply input mapping to prepare agent inputs
        mapped_data = []
        for record in merged_data:
            # Extract mapped values from record
            agent_input = {}
            for placeholder, column_ref in input_mapping.items():
                # column_ref format can be:
                # - "node_1.column_name" (database column)
                # - "node_1.user_input" (trigger field)
                # - "node_1._trigger.type" (nested trigger field)

                # Remove node prefix (everything before first dot)
                if '.' in column_ref:
                    parts = column_ref.split('.', 1)  # Split only on first dot
                    field_path = parts[1]  # Get everything after node_id
                else:
                    field_path = column_ref

                # Handle nested paths (e.g., "_trigger.type")
                if '.' in field_path:
                    # Navigate nested structure
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

            mapped_data.append({
                'original_record': record,
                'agent_input': agent_input
            })

        # Split into batches
        batches = []
        for i in range(0, len(mapped_data), batch_size):
            batches.append(mapped_data[i:i + batch_size])

        # Get agent configuration
        agent_id = config.get('agent_id')
        llm_credential_id = config.get('llm_credential_id')
        model = config.get('model')  # Optional - can be None/empty

        # Load agent from database
        try:
            agent = Agent.objects.get(id=agent_id, is_active=True)
        except Agent.DoesNotExist:
            raise ValueError(f"Agent with ID {agent_id} not found or inactive")

        # Create AgentExecutor
        executor = AgentExecutor(agent_id=agent_id)

        # Process batches
        all_results = []
        for batch_idx, batch in enumerate(batches):
            batch_results = []

            for item in batch:
                placeholder_values = item['agent_input']

                # Execute agent based on return type
                if agent.return_type == 'structured':
                    # Structured agent - returns JSON
                    result = executor.execute_structured(
                        placeholder_values=placeholder_values,
                        credential_id=int(llm_credential_id),
                        model=model if model else None,
                        mcp_server_ids=mcp_server_ids,
                        internal_tool_attachments=internal_tool_attachments
                    )

                    if result['success']:
                        # Merge agent output with original record
                        processed_record = {
                            **item['original_record'],  # Original columns
                            **result['output'],  # Agent output fields (spreads JSON into record)
                            '_agent_metadata': {
                                'execution_time_ms': result['execution_time_ms'],
                                'success': True,
                                'agent_type': 'structured'
                            }
                        }
                    else:
                        # Execution failed - preserve record with error
                        processed_record = {
                            **item['original_record'],
                            '_agent_metadata': {
                                'execution_time_ms': result['execution_time_ms'],
                                'success': False,
                                'error': result['error'],
                                'agent_type': 'structured'
                            }
                        }

                else:
                    # Unstructured agent - returns text response
                    # Load agent prompts and substitute placeholders
                    prompts = Prompt.objects.filter(agent=agent, is_active=True)
                    user_prompt_template = ""
                    for prompt in prompts:
                        if prompt.prompt_type == 'user':
                            user_prompt_template = prompt.content
                            break

                    # Substitute placeholders in the user prompt
                    # Pattern: {{placeholder}} -> value from placeholder_values
                    def replace_placeholder(match):
                        placeholder_name = match.group(1)
                        return str(placeholder_values.get(placeholder_name, f"{{{{{placeholder_name}}}}}"))

                    substituted_message = re.sub(r'\{\{(\w+)\}\}', replace_placeholder, user_prompt_template)

                    print(f"[AGENT NODE DEBUG] Unstructured agent prompt substitution:")
                    print(f"  - Template: {user_prompt_template[:200]}")
                    print(f"  - Placeholder values: {placeholder_values}")
                    print(f"  - Substituted message: {substituted_message[:200]}")

                    result = executor.execute_unstructured(
                        message=substituted_message,
                        credential_id=int(llm_credential_id),
                        conversation_history=None,  # No conversation context in workflows
                        model=model if model else None,
                        mcp_server_ids=mcp_server_ids,
                        internal_tool_attachments=internal_tool_attachments
                    )

                    if result['success']:
                        processed_record = {
                            **item['original_record'],
                            'agent_response': result['response'],  # Text response
                            '_agent_metadata': {
                                'execution_time_ms': result['execution_time_ms'],
                                'success': True,
                                'agent_type': 'unstructured'
                            }
                        }
                    else:
                        processed_record = {
                            **item['original_record'],
                            '_agent_metadata': {
                                'execution_time_ms': result['execution_time_ms'],
                                'success': False,
                                'error': result['error'],
                                'agent_type': 'unstructured'
                            }
                        }

                batch_results.append(processed_record)

            all_results.extend(batch_results)

        return all_results

    def _get_toolbox_config(self):
        """
        Check for connected toolbox node and return its configuration.

        Looks for incoming edges with targetHandle='tools-input' (bottom handle).
        If found, executes the toolbox node and returns its configuration.

        Returns:
            dict or None: Toolbox configuration containing mcp_server_ids and
                         internal_tool_attachments, or None if no toolbox connected
        """
        from workflows.models import Workflow, WorkflowNode
        from workflows.execution.node_handlers.factory import NodeFactory

        try:
            # Get workflow
            workflow = Workflow.objects.get(id=self.workflow_id)

            # Get edges from workflow configuration
            edges = workflow.configuration.get('edges', [])

            # Find toolbox edges (target is this node, targetHandle is 'tools-input')
            toolbox_edges = [
                edge for edge in edges
                if edge.get('target') == self.node_id and edge.get('targetHandle') == 'tools-input'
            ]

            if not toolbox_edges:
                print(f"[AGENT NODE] No toolbox connected")
                return None

            # Should only be one toolbox per agent (enforced by frontend)
            if len(toolbox_edges) > 1:
                print(f"[AGENT NODE] WARNING: Multiple toolboxes found ({len(toolbox_edges)}), using first")

            toolbox_edge = toolbox_edges[0]
            toolbox_node_id = toolbox_edge.get('source')

            print(f"[AGENT NODE] Found toolbox connection from node {toolbox_node_id}")

            # Get toolbox node
            toolbox_node = WorkflowNode.objects.get(
                id=toolbox_node_id,
                workflow=workflow,
                is_active=True
            )

            # Verify it's actually a toolbox node
            if toolbox_node.node_type != 'toolbox':
                print(f"[AGENT NODE] WARNING: Node {toolbox_node_id} is not a toolbox (type: {toolbox_node.node_type})")
                return None

            # Create toolbox node instance
            toolbox_instance = NodeFactory.create_node(
                node_id=toolbox_node.id,
                node_type=toolbox_node.node_type,
                configuration=toolbox_node.configuration,
                workflow_id=self.workflow_id,
                execution_id=self.execution_id,
                position=toolbox_node.position
            )

            # Execute toolbox (returns configuration)
            toolbox_config = toolbox_instance.run()

            print(f"[AGENT NODE] Toolbox configuration retrieved successfully")
            return toolbox_config

        except (Workflow.DoesNotExist, WorkflowNode.DoesNotExist) as e:
            print(f"[AGENT NODE] Error retrieving toolbox config: {e}")
            return None
        except Exception as e:
            print(f"[AGENT NODE] Unexpected error getting toolbox config: {e}")
            import traceback
            traceback.print_exc()
            return None
