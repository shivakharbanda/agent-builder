"""
Base Tool Class

Abstract base class for all internal tools.
Internal tools can be used both in PydanticAI agents and as workflow nodes.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional
from credentials.models import Credential


class BaseTool(ABC):
    """
    Abstract base class for internal tools.

    All internal tools must inherit from this class and implement required methods.
    Tools can be used in two modes:
    1. Agent Mode: Injected into PydanticAI agents as callable tools
    2. Workflow Node Mode: Executed directly as workflow nodes

    Attributes:
        tool_name (str): Unique identifier for the tool
        display_name (str): Human-readable name for UI
        description (str): Description of what the tool does
        requires_credential (bool): Whether tool needs a credential
        required_credential_type (str): Type of credential needed (e.g., 'SERP API')
        input_schema (dict): JSON schema defining tool inputs
        output_schema (dict): JSON schema defining tool outputs
        category (str): Tool category for organization (e.g., 'search', 'communication')
    """

    # Class-level attributes (override in subclasses)
    tool_name: str = None
    display_name: str = None
    description: str = None
    requires_credential: bool = False
    required_credential_type: str = None
    input_schema: Dict[str, Any] = {}
    output_schema: Dict[str, Any] = {}
    category: str = "general"

    @classmethod
    @abstractmethod
    async def execute(cls, credential: Optional[Credential], **kwargs) -> Any:
        """
        Execute the tool's main logic with credential injected.

        This method contains the actual tool implementation.
        Credentials are injected here, not exposed to LLM.

        Args:
            credential: Credential object containing API keys/secrets
            **kwargs: Tool-specific input parameters

        Returns:
            Any: Tool execution result

        Raises:
            ValueError: If required parameters are missing
            Exception: If tool execution fails
        """
        pass

    @classmethod
    def get_pydantic_tool(cls, credential: Optional[Credential]):
        """
        Create PydanticAI compatible tool function with credential in closure.

        This method wraps the execute() method to create a tool that can be
        registered with PydanticAI agents. The credential is captured in the
        closure and NOT exposed to the LLM.

        Args:
            credential: Credential to inject into tool

        Returns:
            Callable: PydanticAI @tool decorated function

        Example:
            tool_fn = SerpApiTool.get_pydantic_tool(my_credential)
            agent = PydanticAgent(model=llm, toolsets=[tool_fn])
        """
        # Create wrapper function that captures credential in closure
        async def tool_wrapper(**kwargs) -> Any:
            """Tool wrapper with credential injected"""
            return await cls.execute(credential, **kwargs)

        # Set function metadata for PydanticAI
        tool_wrapper.__name__ = cls.tool_name
        tool_wrapper.__doc__ = cls.description

        return tool_wrapper

    @classmethod
    def validate_inputs(cls, inputs: Dict[str, Any]) -> bool:
        """
        Validate tool inputs against input schema.

        Args:
            inputs: Input parameters to validate

        Returns:
            bool: True if inputs are valid

        Raises:
            ValueError: If inputs are invalid
        """
        # Get required fields from schema
        schema = cls.input_schema
        required_fields = schema.get('required', [])

        # Check all required fields are present
        for field in required_fields:
            if field not in inputs:
                raise ValueError(f"Missing required field: {field}")

        return True

    @classmethod
    def get_metadata(cls) -> Dict[str, Any]:
        """
        Get tool metadata for registration and UI display.

        Returns:
            dict: Tool metadata including name, description, schemas, etc.
        """
        return {
            'tool_name': cls.tool_name,
            'display_name': cls.display_name or cls.tool_name,
            'description': cls.description,
            'requires_credential': cls.requires_credential,
            'required_credential_type': cls.required_credential_type,
            'input_schema': cls.input_schema,
            'output_schema': cls.output_schema,
            'category': cls.category,
        }

    @classmethod
    def __repr__(cls) -> str:
        """String representation of tool class."""
        return f"<{cls.__name__}(name={cls.tool_name}, category={cls.category})>"
