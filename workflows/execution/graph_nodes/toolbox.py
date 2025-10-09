"""
Toolbox Node for Pydantic AI Graph

Provides tool attachments (MCP servers + internal tools) to agent nodes.
This is a configuration-only node that is queried by agents, not in the main execution flow.
"""

from typing import Any, Dict
from pydantic_graph import GraphRunContext
from workflows.execution.graph_nodes.base import DynamicWorkflowNode
from workflows.execution.state import WorkflowState


class ToolboxNode(DynamicWorkflowNode):
    """
    Toolbox node for providing tools to agents.

    This node is NOT in the main execution flow. Instead, agent nodes query it
    by looking for edges with targetHandle='tools-input' and executing the toolbox
    to get its configuration.

    Configuration:
        mcp_server_ids: List of MCP server IDs
        internal_tool_attachments: List of {tool_id, credential_id} dicts

    Returns:
        dict: Tool configuration for agent to use
    """

    async def execute(self, ctx: GraphRunContext[WorkflowState]) -> Dict[str, Any]:
        """
        Execute toolbox - return tool configuration.

        This is called by the agent node to get tool attachments, not by
        the main workflow execution flow.

        Args:
            ctx: Graph run context

        Returns:
            dict: Tool configuration containing MCP servers and internal tools
        """
        config = self.configuration

        mcp_server_ids = config.get('mcp_server_ids', [])
        internal_tool_attachments = config.get('internal_tool_attachments', [])

        print(f"\n[TOOLBOX NODE {self.node_id}] Providing tool configuration")
        print(f"  - MCP Servers: {len(mcp_server_ids)}")
        print(f"  - Internal Tools: {len(internal_tool_attachments)}")

        # Return configuration for agent to use
        return {
            'mcp_server_ids': mcp_server_ids,
            'internal_tool_attachments': internal_tool_attachments,
            'summary': {
                'mcp_count': len(mcp_server_ids),
                'internal_tool_count': len(internal_tool_attachments),
                'total_tools': len(mcp_server_ids) + len(internal_tool_attachments)
            }
        }
