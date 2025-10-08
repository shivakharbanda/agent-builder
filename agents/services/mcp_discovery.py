"""
MCP Server Discovery Service

Connects to MCP servers, fetches tool schemas, and stores them in database.
"""

import asyncio
from typing import Dict, List
from django.utils import timezone
from asgiref.sync import sync_to_async
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client
from agents.models import MCPServer, MCPToolDefinition


class MCPDiscoveryService:
    """Service for discovering and syncing MCP server tools"""

    @staticmethod
    def _get_mcp_session(url: str, transport: str = 'http'):
        """
        Create MCP session based on transport type.

        Args:
            url: MCP server endpoint
            transport: Transport type ('http', 'sse', 'stdio')

        Returns:
            Async context manager for MCP session

        Note:
            Currently only 'http' transport is fully supported for discovery.
            SSE and stdio transports can be added as needed.
        """
        if transport == 'http':
            return streamablehttp_client(url)
        elif transport == 'sse':
            # SSE transport - for now, treat as HTTP
            # TODO: Implement proper SSE client if needed
            return streamablehttp_client(url)
        else:
            raise ValueError(f"Unsupported transport type: {transport}")

    @staticmethod
    async def test_connection(url: str, transport: str = 'http') -> Dict:
        """
        Test connectivity to MCP server using proper MCP protocol.

        Args:
            url: MCP server endpoint (e.g., 'http://localhost:8005/mcp')
            transport: Transport type ('http', 'sse', 'stdio')

        Returns:
            {"healthy": bool, "error": str|None, "tools_count": int}
        """
        try:
            # Get MCP session based on transport
            async with MCPDiscoveryService._get_mcp_session(url, transport) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    # Initialize session (handshake)
                    await session.initialize()

                    # List available tools
                    tools_result = await session.list_tools()

                    return {
                        "healthy": True,
                        "error": None,
                        "tools_count": len(tools_result.tools)
                    }
        except asyncio.TimeoutError:
            return {"healthy": False, "error": "Connection timeout", "tools_count": 0}
        except Exception as e:
            return {"healthy": False, "error": str(e), "tools_count": 0}

    @staticmethod
    async def discover_tools(url: str, tool_prefix: str = "", transport: str = 'http') -> Dict:
        """
        Discover tools from MCP server without saving to database.

        Used for previewing tools before registration.

        Args:
            url: MCP server endpoint (e.g., 'http://localhost:8005/mcp')
            tool_prefix: Optional prefix for tool names
            transport: Transport type ('http', 'sse', 'stdio')

        Returns:
            {
                "healthy": bool,
                "tools": List[Dict],
                "error": str|None
            }
        """
        try:
            # Get MCP session based on transport
            async with MCPDiscoveryService._get_mcp_session(url, transport) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    # Initialize session (handshake)
                    await session.initialize()

                    # List available tools
                    tools_result = await session.list_tools()

                    # Parse tools
                    tools = []
                    for tool_def in tools_result.tools:
                        # Build prefixed name
                        if tool_prefix:
                            prefixed_name = f"{tool_prefix}_{tool_def.name}"
                        else:
                            prefixed_name = tool_def.name

                        # Extract input schema and required inputs
                        input_schema = tool_def.inputSchema if hasattr(tool_def, 'inputSchema') else {}
                        if isinstance(input_schema, dict):
                            required_inputs = input_schema.get('required', [])
                        else:
                            # If inputSchema is an object, try to convert to dict
                            required_inputs = getattr(input_schema, 'required', []) if hasattr(input_schema, 'required') else []

                        # Extract capabilities
                        description = tool_def.description if hasattr(tool_def, 'description') else ''
                        capabilities = MCPDiscoveryService._extract_capabilities(description)

                        # Bulletproof: Convert None to appropriate defaults
                        tools.append({
                            'name': tool_def.name,
                            'prefixed_name': prefixed_name,
                            'title': (getattr(tool_def, 'title', None) or ''),
                            'description': (description or ''),
                            'input_schema': (input_schema if isinstance(input_schema, dict) else {}) or {},
                            'output_schema': getattr(tool_def, 'outputSchema', None),
                            'capabilities_tags': (capabilities or []),
                            'required_inputs': (required_inputs or [])
                        })

                    return {
                        "healthy": True,
                        "tools": tools,
                        "error": None
                    }

        except asyncio.TimeoutError:
            return {"healthy": False, "tools": [], "error": "Connection timeout"}
        except Exception as e:
            return {"healthy": False, "tools": [], "error": str(e)}

    @staticmethod
    async def sync_server_schema(server_id: int) -> Dict:
        """
        Fetch MCP server schema and update tool definitions using MCP protocol.

        Args:
            server_id: ID of MCPServer record

        Returns:
            {
                "tools_discovered": int,
                "tools_stored": int,
                "server_healthy": bool,
                "error": str|None
            }
        """
        try:
            server = await sync_to_async(MCPServer.objects.get)(id=server_id)

            # STEP 1: Fetch tools from MCP server (async operation)
            tools_data = []
            async with MCPDiscoveryService._get_mcp_session(server.url, server.transport) as (read_stream, write_stream, _):
                async with ClientSession(read_stream, write_stream) as session:
                    # Initialize session (handshake)
                    await session.initialize()

                    # List available tools
                    tools_result = await session.list_tools()

                    # Parse tools into plain dicts (while still in MCP session)
                    for tool_def in tools_result.tools:
                        # Build prefixed name
                        if server.tool_prefix:
                            prefixed_name = f"{server.tool_prefix}_{tool_def.name}"
                        else:
                            prefixed_name = tool_def.name

                        # Extract input schema and required inputs
                        input_schema = tool_def.inputSchema if hasattr(tool_def, 'inputSchema') else {}
                        if isinstance(input_schema, dict):
                            required_inputs = input_schema.get('required', [])
                        else:
                            required_inputs = getattr(input_schema, 'required', []) if hasattr(input_schema, 'required') else []

                        # Extract capabilities (basic keyword matching)
                        description = tool_def.description if hasattr(tool_def, 'description') else ''
                        capabilities = MCPDiscoveryService._extract_capabilities(description)

                        # Bulletproof: Convert None to appropriate defaults for NOT NULL fields
                        tools_data.append({
                            'name': tool_def.name,
                            'prefixed_name': prefixed_name,
                            'title': (getattr(tool_def, 'title', None) or ''),  # NOT NULL: must be ''
                            'description': (description or ''),  # NOT NULL: must be ''
                            'input_schema': (input_schema if isinstance(input_schema, dict) else {}) or {},  # NOT NULL: must be {}
                            'output_schema': getattr(tool_def, 'outputSchema', None),  # CAN be None
                            'annotations': getattr(tool_def, 'annotations', None),  # CAN be None
                            'meta': getattr(tool_def, 'meta', None),  # CAN be None
                            'capabilities_tags': (capabilities or []),  # NOT NULL: must be []
                            'required_inputs': (required_inputs or [])  # NOT NULL: must be []
                        })

            # STEP 2: MCP session is now closed, do database operations
            # Clear old tool definitions
            await sync_to_async(lambda: MCPToolDefinition.objects.filter(server=server).delete())()

            # Store new tools
            tools_stored = 0
            for tool_data in tools_data:
                await sync_to_async(MCPToolDefinition.objects.create)(
                    server=server,
                    **tool_data
                )
                tools_stored += 1

            # Update server metadata
            server.is_healthy = True
            server.last_schema_sync = timezone.now()
            await sync_to_async(server.save)()

            return {
                "tools_discovered": len(tools_data),
                "tools_stored": tools_stored,
                "server_healthy": True,
                "error": None
            }

        except MCPServer.DoesNotExist:
            return {
                "tools_discovered": 0,
                "tools_stored": 0,
                "server_healthy": False,
                "error": "Server not found"
            }
        except Exception as e:
            # Mark server as unhealthy
            try:
                server = await sync_to_async(MCPServer.objects.get)(id=server_id)
                server.is_healthy = False
                await sync_to_async(server.save)()
            except:
                pass

            return {
                "tools_discovered": 0,
                "tools_stored": 0,
                "server_healthy": False,
                "error": str(e)
            }

    @staticmethod
    def _extract_capabilities(description: str) -> List[str]:
        """Extract capability tags from tool description using keyword matching"""
        capabilities = []

        keywords = {
            'web': ['web', 'url', 'website', 'crawl', 'scrape', 'html'],
            'image': ['screenshot', 'image', 'png', 'jpg'],
            'pdf': ['pdf', 'document'],
            'markdown': ['markdown', 'md'],
            'javascript': ['javascript', 'js', 'execute'],
            'data': ['extract', 'parse', 'data'],
        }

        description_lower = description.lower()
        for capability, terms in keywords.items():
            if any(term in description_lower for term in terms):
                capabilities.append(capability)

        return capabilities
