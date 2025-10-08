"""
Internal Tool Node Handler

Executes internal tools as standalone workflow nodes.
Tools are executed directly (not through an LLM agent).
"""

import asyncio
from typing import Any, Dict
from .base import BaseNode
from agents.tools import get_tool
from agents.models import InternalTool
from credentials.models import Credential


class InternalToolNode(BaseNode):
    """
    Node handler for executing internal tools in workflows.

    Internal tools are executed directly with credential injection,
    without involving an LLM. This allows tools to be used as
    standalone data processing steps in workflows.

    Configuration:
        {
            "tool_id": 123,            # InternalTool database ID
            "credential_id": 456,      # Credential database ID
            "inputs": {                # Tool input parameters
                "query": "{{previous_node.output.search_query}}",  # Can reference context
                "num_results": 10
            },
            "input_mapping": {         # Optional: map input_data to tool params
                "query": "$.search_text"  # JSONPath from input_data
            }
        }

    Example:
        # Direct inputs
        config = {
            "tool_id": 1,
            "credential_id": 5,
            "inputs": {
                "query": "Python tutorials",
                "num_results": 5
            }
        }

        # Inputs from previous node
        config = {
            "tool_id": 1,
            "credential_id": 5,
            "inputs": {
                "query": "{{input.search_query}}"  # From input_data
            },
            "input_mapping": {
                "query": "$.user_query"  # Extract from input_data JSON
            }
        }
    """

    node_type = 'internal_tool'
    category = 'tools'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tool = None
        self.credential = None
        self.tool_class = None

    def validate(self) -> bool:
        """
        Validate node configuration.

        Returns:
            bool: True if configuration is valid

        Raises:
            ValueError: If configuration is invalid
        """
        # Check required fields
        required_fields = ['tool_id', 'credential_id']
        for field in required_fields:
            if field not in self.configuration:
                raise ValueError(f"Missing required configuration field: {field}")

        # Validate tool exists
        tool_id = self.configuration['tool_id']
        try:
            self.tool = InternalTool.objects.get(id=tool_id, is_active=True)
        except InternalTool.DoesNotExist:
            raise ValueError(f"InternalTool with ID {tool_id} not found or inactive")

        # Check if tool is enabled
        if not self.tool.is_enabled:
            raise ValueError(f"Tool '{self.tool.name}' is disabled")

        # Validate credential exists
        credential_id = self.configuration['credential_id']
        try:
            self.credential = Credential.objects.get(id=credential_id, is_active=True, is_deleted=False)
        except Credential.DoesNotExist:
            raise ValueError(f"Credential with ID {credential_id} not found or inactive")

        # Validate credential type matches tool requirement
        if self.tool.required_credential_type:
            if self.credential.credential_type != self.tool.required_credential_type:
                raise ValueError(
                    f"Credential type mismatch: Tool requires '{self.tool.required_credential_type.type_name}', "
                    f"but credential is '{self.credential.credential_type.type_name}'"
                )

        # Load tool class from registry
        try:
            self.tool_class = get_tool(self.tool.tool_type)
        except KeyError:
            raise ValueError(
                f"Tool type '{self.tool.tool_type}' not found in registry. "
                f"Is the tool implementation missing?"
            )

        # Validate inputs if provided
        if 'inputs' in self.configuration:
            inputs = self.configuration['inputs']
            if not isinstance(inputs, dict):
                raise ValueError("'inputs' must be a dictionary")

            # Validate against tool input schema (basic validation)
            try:
                # This will raise ValueError if required fields are missing
                # Note: We can't validate fully here since inputs might have template variables
                pass  # Skip validation for now, will validate at runtime
            except Exception as e:
                print(f"[INTERNAL TOOL NODE] Warning: Input validation failed: {e}")

        return True

    def execute(self, input_data: Any = None) -> Any:
        """
        Execute the internal tool.

        Args:
            input_data: Data from previous node (optional)

        Returns:
            Any: Tool execution result

        Raises:
            Exception: If tool execution fails
        """
        print(f"\n[INTERNAL TOOL NODE] Executing tool: {self.tool.name}")
        print(f"[INTERNAL TOOL NODE] Tool Type: {self.tool.tool_type}")
        print(f"[INTERNAL TOOL NODE] Credential: {self.credential.name}")

        # Get tool inputs
        raw_inputs = self.configuration.get('inputs', {})
        input_mapping = self.configuration.get('input_mapping', {})

        # Resolve inputs (substitute templates, apply mappings)
        resolved_inputs = self._resolve_inputs(raw_inputs, input_data, input_mapping)

        print(f"[INTERNAL TOOL NODE] Resolved Inputs: {resolved_inputs}")

        # Validate resolved inputs against tool schema
        try:
            self.tool_class.validate_inputs(resolved_inputs)
        except ValueError as e:
            raise ValueError(f"Tool input validation failed: {e}")

        # Execute tool
        try:
            # Run async tool execution
            result = asyncio.run(self.tool_class.execute(
                credential=self.credential,
                **resolved_inputs
            ))

            print(f"[INTERNAL TOOL NODE] Tool execution successful")
            print(f"[INTERNAL TOOL NODE] Result keys: {list(result.keys()) if isinstance(result, dict) else type(result)}")

            return result

        except Exception as e:
            print(f"[INTERNAL TOOL NODE] Tool execution failed: {e}")
            raise Exception(f"Internal tool '{self.tool.name}' execution failed: {str(e)}")

    def _resolve_inputs(self, raw_inputs: Dict, input_data: Any, input_mapping: Dict) -> Dict:
        """
        Resolve tool inputs by applying templates and mappings.

        Args:
            raw_inputs: Raw input configuration (may contain templates)
            input_data: Data from previous node
            input_mapping: JSONPath mappings from input_data

        Returns:
            dict: Resolved input parameters
        """
        resolved = {}

        # First, apply input_mapping to extract values from input_data
        if input_data and input_mapping:
            for param_name, json_path in input_mapping.items():
                try:
                    # Simple JSONPath extraction (basic implementation)
                    value = self._extract_json_path(input_data, json_path)
                    if value is not None:
                        resolved[param_name] = value
                except Exception as e:
                    print(f"[INTERNAL TOOL NODE] Warning: Failed to extract '{json_path}': {e}")

        # Second, process raw_inputs (may override mapped values)
        for param_name, param_value in raw_inputs.items():
            # Check if value is a template like "{{input.field}}"
            if isinstance(param_value, str) and param_value.startswith('{{') and param_value.endswith('}}'):
                # Extract template variable
                template_var = param_value[2:-2].strip()

                # Resolve template from input_data
                if template_var.startswith('input.') and input_data:
                    field_path = template_var[6:]  # Remove "input." prefix
                    try:
                        value = self._extract_field(input_data, field_path)
                        resolved[param_name] = value
                    except Exception as e:
                        print(f"[INTERNAL TOOL NODE] Warning: Failed to resolve template '{template_var}': {e}")
                        resolved[param_name] = param_value  # Keep original
                else:
                    # Unknown template, keep original
                    resolved[param_name] = param_value
            else:
                # Direct value (not a template)
                resolved[param_name] = param_value

        return resolved

    def _extract_json_path(self, data: Any, path: str) -> Any:
        """
        Extract value from data using JSONPath (basic implementation).

        Args:
            data: Data to extract from
            path: JSONPath expression (e.g., "$.user.name", "$.items[0]")

        Returns:
            Any: Extracted value or None
        """
        # Basic JSONPath implementation
        # Full implementation would use jsonpath library

        # Remove leading "$." if present
        if path.startswith('$.'):
            path = path[2:]

        # Split path by dots
        parts = path.split('.')

        current = data
        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                current = current[index] if 0 <= index < len(current) else None
            else:
                return None

            if current is None:
                return None

        return current

    def _extract_field(self, data: Any, field_path: str) -> Any:
        """
        Extract field from data using dot notation.

        Args:
            data: Data to extract from
            field_path: Field path (e.g., "user.name", "items[0].id")

        Returns:
            Any: Extracted value

        Raises:
            KeyError: If field not found
        """
        parts = field_path.split('.')
        current = data

        for part in parts:
            if isinstance(current, dict):
                current = current[part]  # Raises KeyError if missing
            elif isinstance(current, list) and part.isdigit():
                index = int(part)
                current = current[index]  # Raises IndexError if out of bounds
            else:
                raise KeyError(f"Cannot extract '{part}' from {type(current)}")

        return current

    def check_dependencies(self) -> bool:
        """
        Check if all dependencies are available.

        Returns:
            bool: True if dependencies are available
        """
        # Check if tool exists in registry
        try:
            get_tool(self.configuration.get('tool_type', ''))
            return True
        except KeyError:
            return False
