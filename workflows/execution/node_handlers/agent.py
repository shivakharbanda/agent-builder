"""
Agent Node Handler

Handles execution of AI agent nodes.
Processes data using configured AI agents.
"""

from typing import Any
from .base import BaseNode


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
        self.optional_dependencies = ['batch_size', 'timeout', 'input_mapping']

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
            1. Validate input is list of dicts
            2. Apply input_mapping to transform data
            3. Split into batches based on batch_size
            4. Process each batch (currently mocked)
            5. Aggregate and return results
        """
        from datetime import datetime
        import time

        config = self.configuration

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

        if not isinstance(input_data, list):
            raise ValueError("Agent node expects input_data to be a list of records")

        # If no records, return empty
        if len(input_data) == 0:
            return []

        # Apply input mapping to prepare agent inputs
        mapped_data = []
        for record in input_data:
            # Extract mapped values from record
            agent_input = {}
            for placeholder, column_ref in input_mapping.items():
                # column_ref format: "node_1.column_name" or just "column_name"
                column_name = column_ref.split('.')[-1] if '.' in column_ref else column_ref

                # Get value from record
                if column_name in record:
                    agent_input[placeholder] = record[column_name]
                else:
                    agent_input[placeholder] = None

            mapped_data.append({
                'original_record': record,
                'agent_input': agent_input
            })

        # Split into batches
        batches = []
        for i in range(0, len(mapped_data), batch_size):
            batches.append(mapped_data[i:i + batch_size])

        # Process batches
        all_results = []
        for batch_idx, batch in enumerate(batches):
            # Mock agent execution for each record in batch
            # TODO: Replace with actual agent API call
            batch_results = []
            for item in batch:
                # Simulate processing
                mock_result = {
                    **item['original_record'],  # Preserve original columns
                    'agent_result': f'Mock classification result',  # Mock agent output
                    'agent_confidence': 0.95,  # Mock confidence score
                    'agent_processed_at': datetime.now().isoformat(),
                    'agent_input_used': item['agent_input']  # Show what was sent to agent
                }
                batch_results.append(mock_result)

            all_results.extend(batch_results)

            # Simulate batch processing delay (remove in production)
            time.sleep(0.1)

        return all_results
