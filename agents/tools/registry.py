"""
Tool Registry

Central registry for all internal tools.
Maps tool type strings to tool classes.
"""

from typing import Dict, List, Type
from .base import BaseTool


# Global registry mapping tool_type to tool class
TOOL_REGISTRY: Dict[str, Type[BaseTool]] = {}


def register_tool(tool_type: str, tool_class: Type[BaseTool]):
    """
    Register a tool in the registry.

    Args:
        tool_type: Unique identifier for the tool (e.g., 'serp_api')
        tool_class: Tool class that inherits from BaseTool

    Raises:
        ValueError: If tool_class doesn't inherit from BaseTool
        ValueError: If tool_type is already registered
    """
    if not issubclass(tool_class, BaseTool):
        raise ValueError(f"Tool class {tool_class.__name__} must inherit from BaseTool")

    if tool_type in TOOL_REGISTRY:
        raise ValueError(f"Tool type '{tool_type}' is already registered")

    TOOL_REGISTRY[tool_type] = tool_class
    print(f"[TOOL REGISTRY] Registered tool: {tool_type} -> {tool_class.__name__}")


def get_tool(tool_type: str) -> Type[BaseTool]:
    """
    Get tool class from registry.

    Args:
        tool_type: Tool type identifier

    Returns:
        BaseTool: Tool class

    Raises:
        KeyError: If tool_type not found in registry
    """
    if tool_type not in TOOL_REGISTRY:
        available = ', '.join(TOOL_REGISTRY.keys()) or 'none'
        raise KeyError(
            f"Tool type '{tool_type}' not found in registry. "
            f"Available tools: {available}"
        )

    return TOOL_REGISTRY[tool_type]


def get_all_tools() -> Dict[str, Type[BaseTool]]:
    """
    Get all registered tools.

    Returns:
        dict: Dictionary mapping tool_type to tool class
    """
    return TOOL_REGISTRY.copy()


def get_tool_metadata(tool_type: str) -> dict:
    """
    Get metadata for a specific tool.

    Args:
        tool_type: Tool type identifier

    Returns:
        dict: Tool metadata
    """
    tool_class = get_tool(tool_type)
    return tool_class.get_metadata()


def get_all_tool_metadata() -> List[dict]:
    """
    Get metadata for all registered tools.

    Returns:
        list: List of tool metadata dicts
    """
    return [tool_class.get_metadata() for tool_class in TOOL_REGISTRY.values()]


def is_registered(tool_type: str) -> bool:
    """
    Check if a tool type is registered.

    Args:
        tool_type: Tool type to check

    Returns:
        bool: True if registered
    """
    return tool_type in TOOL_REGISTRY


def load_builtin_tools():
    """
    Load and register all built-in tools.

    This function imports and registers all tool implementations.
    Called automatically when the module is imported.
    """
    # Import tool implementations here to avoid circular imports
    try:
        from .serp_api import SerpApiTool
        register_tool('serp_api', SerpApiTool)
    except ImportError as e:
        print(f"[TOOL REGISTRY] Warning: Could not import SerpApiTool: {e}")

    # Future tools:
    # from .weather import WeatherTool
    # register_tool('weather', WeatherTool)

    # from .email import EmailTool
    # register_tool('email', EmailTool)

    print(f"[TOOL REGISTRY] Loaded {len(TOOL_REGISTRY)} built-in tools")


# Auto-load built-in tools on module import
load_builtin_tools()
