"""
MCP Server Discovery Service

Connects to MCP servers, fetches tool schemas, and stores them in database.
"""

import httpx
import asyncio
from typing import Dict, List
from django.utils import timezone
from asgiref.sync import sync_to_async
from agents.models import MCPServer, MCPToolDefinition


class MCPDiscoveryService:
    """Service for discovering and syncing MCP server tools"""

    @staticmethod
    async def test_connection(url: str) -> Dict:
        """
        Test connectivity to MCP server.

        Args:
            url: MCP server SSE endpoint

        Returns:
            {"healthy": bool, "error": str|None, "tools_count": int}
        """
        try:
            # Extract base URL (remove /sse suffix)
            base_url = url.rstrip('/').replace('/mcp/sse', '')
            schema_url = f"{base_url}/mcp/schema"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(schema_url)
                response.raise_for_status()

                # Verify it's valid MCP schema
                schema = response.json()
                if 'tools' not in schema:
                    return {"healthy": False, "error": "Invalid MCP schema - missing 'tools'"}

                return {
                    "healthy": True,
                    "error": None,
                    "tools_count": len(schema.get('tools', []))
                }
        except httpx.TimeoutException:
            return {"healthy": False, "error": "Connection timeout"}
        except httpx.HTTPError as e:
            return {"healthy": False, "error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"healthy": False, "error": str(e)}

    @staticmethod
    async def discover_tools(url: str, tool_prefix: str = "") -> Dict:
        """
        Discover tools from MCP server without saving to database.

        Used for previewing tools before registration.

        Args:
            url: MCP server SSE endpoint
            tool_prefix: Optional prefix for tool names

        Returns:
            {
                "healthy": bool,
                "tools": List[Dict],
                "error": str|None
            }
        """
        try:
            # Extract base URL (remove /sse suffix)
            base_url = url.rstrip('/').replace('/mcp/sse', '')
            schema_url = f"{base_url}/mcp/schema"

            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(schema_url)
                response.raise_for_status()

                # Verify it's valid MCP schema
                schema = response.json()
                if 'tools' not in schema:
                    return {
                        "healthy": False,
                        "tools": [],
                        "error": "Invalid MCP schema - missing 'tools'"
                    }

                # Parse tools
                tools = []
                for tool_def in schema.get('tools', []):
                    # Build prefixed name
                    if tool_prefix:
                        prefixed_name = f"{tool_prefix}_{tool_def['name']}"
                    else:
                        prefixed_name = tool_def['name']

                    # Extract required inputs
                    input_schema = tool_def.get('inputSchema', {})
                    required_inputs = input_schema.get('required', [])

                    # Extract capabilities
                    capabilities = MCPDiscoveryService._extract_capabilities(
                        tool_def.get('description', '')
                    )

                    tools.append({
                        'name': tool_def['name'],
                        'prefixed_name': prefixed_name,
                        'title': tool_def.get('title', ''),
                        'description': tool_def.get('description', ''),
                        'input_schema': input_schema,
                        'output_schema': tool_def.get('outputSchema'),
                        'capabilities_tags': capabilities,
                        'required_inputs': required_inputs
                    })

                return {
                    "healthy": True,
                    "tools": tools,
                    "error": None
                }

        except httpx.TimeoutException:
            return {"healthy": False, "tools": [], "error": "Connection timeout"}
        except httpx.HTTPError as e:
            return {"healthy": False, "tools": [], "error": f"HTTP error: {str(e)}"}
        except Exception as e:
            return {"healthy": False, "tools": [], "error": str(e)}

    @staticmethod
    async def sync_server_schema(server_id: int) -> Dict:
        """
        Fetch MCP server schema and update tool definitions.

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

            # Extract base URL
            base_url = server.url.rstrip('/').replace('/mcp/sse', '')
            schema_url = f"{base_url}/mcp/schema"

            # Fetch schema
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(schema_url)
                response.raise_for_status()
                schema = response.json()

            # Clear old tool definitions
            await sync_to_async(lambda: MCPToolDefinition.objects.filter(server=server).delete())()

            # Store new tools
            tools_stored = 0
            for tool_def in schema.get('tools', []):
                # Build prefixed name
                if server.tool_prefix:
                    prefixed_name = f"{server.tool_prefix}_{tool_def['name']}"
                else:
                    prefixed_name = tool_def['name']

                # Extract required inputs
                input_schema = tool_def.get('inputSchema', {})
                required_inputs = input_schema.get('required', [])

                # Extract capabilities (basic keyword matching)
                capabilities = MCPDiscoveryService._extract_capabilities(
                    tool_def.get('description', '')
                )

                # Create tool definition
                await sync_to_async(MCPToolDefinition.objects.create)(
                    server=server,
                    name=tool_def['name'],
                    prefixed_name=prefixed_name,
                    title=tool_def.get('title') or '',
                    description=tool_def.get('description') or '',
                    input_schema=input_schema,
                    output_schema=tool_def.get('outputSchema'),
                    annotations=tool_def.get('annotations'),
                    meta=tool_def.get('meta'),
                    capabilities_tags=capabilities,
                    required_inputs=required_inputs
                )
                tools_stored += 1

            # Update server metadata
            server.is_healthy = True
            server.last_schema_sync = timezone.now()
            await sync_to_async(server.save)()

            return {
                "tools_discovered": len(schema.get('tools', [])),
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
