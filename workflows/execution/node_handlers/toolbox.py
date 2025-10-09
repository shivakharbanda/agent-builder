"""
Toolbox Node Handler

Provides tool attachments (MCP servers + internal tools) to agent nodes.
This is a configuration-only node that passes tool selections to connected agents.
"""

from typing import Any, Dict, List, Optional
from .base import BaseNode
from agents.models import MCPServer, InternalTool
from credentials.models import Credential


class ToolboxNode(BaseNode):
    """
    Toolbox node handler for attaching tools to AI agents.

    This node acts as a tool container that connects to agent nodes.
    It doesn't process data itself but provides tool configurations
    to the connected agent for execution.

    Configuration:
        {
            "mcp_server_ids": [1, 2, 3],  # List of MCP server IDs
            "internal_tool_attachments": [  # Internal tools with credentials
                {"tool_id": 1, "credential_id": 5},
                {"tool_id": 3, "credential_id": 7}
            ]
        }

    Connection:
        - Connects TO agent nodes only (bottom handle)
        - One toolbox per agent node (enforced by frontend validation)
        - Agent node reads toolbox config during execution

    Execution:
        - Returns configuration as-is (pass-through)
        - Agent node extracts tool IDs and passes to AgentExecutor
    """

    node_type = 'toolbox'
    category = 'tools'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.mcp_servers = []
        self.internal_tools = []

    def validate(self) -> bool:
        """
        Validate toolbox configuration.

        Checks:
        - MCP server IDs exist and are active
        - Internal tool IDs exist and are active
        - Credential IDs exist and are active
        - Credential types match tool requirements

        Returns:
            bool: True if valid

        Raises:
            ValueError: If configuration is invalid
        """
        config = self.configuration

        # Get tool selections
        mcp_server_ids = config.get('mcp_server_ids', [])
        internal_tool_attachments = config.get('internal_tool_attachments', [])

        # Validate MCP servers
        if mcp_server_ids:
            if not isinstance(mcp_server_ids, list):
                raise ValueError("mcp_server_ids must be a list")

            for server_id in mcp_server_ids:
                try:
                    server = MCPServer.objects.get(id=server_id, is_active=True)
                    self.mcp_servers.append(server)
                    print(f"[TOOLBOX NODE] Validated MCP server: {server.name} (ID: {server_id})")
                except MCPServer.DoesNotExist:
                    raise ValueError(f"MCP Server with ID {server_id} not found or inactive")

        # Validate internal tools with credentials
        if internal_tool_attachments:
            if not isinstance(internal_tool_attachments, list):
                raise ValueError("internal_tool_attachments must be a list")

            for idx, attachment in enumerate(internal_tool_attachments):
                if not isinstance(attachment, dict):
                    raise ValueError(f"Attachment {idx} must be a dict with tool_id and credential_id")

                tool_id = attachment.get('tool_id')
                credential_id = attachment.get('credential_id')

                if not tool_id or not credential_id:
                    raise ValueError(f"Attachment {idx} missing tool_id or credential_id")

                # Validate tool exists and is active
                try:
                    tool = InternalTool.objects.get(id=tool_id, is_active=True)
                except InternalTool.DoesNotExist:
                    raise ValueError(f"Internal Tool with ID {tool_id} not found or inactive")

                # Validate tool is enabled
                if not tool.is_enabled:
                    raise ValueError(f"Tool '{tool.name}' (ID: {tool_id}) is disabled")

                # Validate credential exists and is active
                try:
                    credential = Credential.objects.get(
                        id=credential_id,
                        is_active=True,
                        is_deleted=False
                    )
                except Credential.DoesNotExist:
                    raise ValueError(f"Credential with ID {credential_id} not found or inactive")

                # Validate credential type matches tool requirement
                if tool.requires_credential and tool.required_credential_type:
                    if credential.credential_type != tool.required_credential_type:
                        raise ValueError(
                            f"Credential type mismatch for tool '{tool.name}': "
                            f"Expected '{tool.required_credential_type.type_name}', "
                            f"got '{credential.credential_type.type_name}'"
                        )

                self.internal_tools.append({
                    'tool': tool,
                    'credential': credential
                })

                print(f"[TOOLBOX NODE] Validated internal tool: {tool.name} with credential: {credential.name}")

        # Must have at least one tool
        if not self.mcp_servers and not self.internal_tools:
            raise ValueError("Toolbox must have at least one MCP server or internal tool")

        print(f"[TOOLBOX NODE] Validation complete: {len(self.mcp_servers)} MCP servers, {len(self.internal_tools)} internal tools")
        return True

    def execute(self, input_data: Any = None) -> Dict[str, Any]:
        """
        Execute toolbox node (pass-through).

        The toolbox doesn't process data itself. It returns its configuration
        so that the connected agent node can extract and use the tools.

        Args:
            input_data: Ignored (toolbox doesn't process data)

        Returns:
            dict: Configuration containing tool IDs for agent to use
                {
                    'mcp_server_ids': [1, 2, 3],
                    'internal_tool_attachments': [
                        {'tool_id': 1, 'credential_id': 5},
                        {'tool_id': 3, 'credential_id': 7}
                    ],
                    'summary': {
                        'mcp_count': 3,
                        'internal_tool_count': 2
                    }
                }
        """
        print(f"\n[TOOLBOX NODE] Executing toolbox node")
        print(f"[TOOLBOX NODE]   - MCP Servers: {len(self.mcp_servers)}")
        print(f"[TOOLBOX NODE]   - Internal Tools: {len(self.internal_tools)}")

        # Return configuration for agent node to consume
        return {
            'mcp_server_ids': self.configuration.get('mcp_server_ids', []),
            'internal_tool_attachments': self.configuration.get('internal_tool_attachments', []),
            'summary': {
                'mcp_count': len(self.mcp_servers),
                'internal_tool_count': len(self.internal_tools),
                'total_tools': len(self.mcp_servers) + len(self.internal_tools)
            }
        }

    def check_dependencies(self) -> bool:
        """
        Check if all dependencies are available.

        Returns:
            bool: True if all tools and credentials are available
        """
        try:
            # Re-validate to check if tools/servers are still active
            self.validate()
            return True
        except Exception as e:
            print(f"[TOOLBOX NODE] Dependency check failed: {e}")
            return False
