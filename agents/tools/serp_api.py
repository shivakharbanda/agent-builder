"""
SERP API Tool

Web search tool using SerpAPI (https://serpapi.com/).
Requires SERP API credential with 'api_key' field.
"""

import httpx
from typing import Any, Dict, Optional, List
from asgiref.sync import sync_to_async
from credentials.models import Credential
from .base import BaseTool


class SerpApiTool(BaseTool):
    """
    SERP API search tool.

    Performs web searches using SerpAPI service. API key is injected
    server-side and not exposed to LLM.

    Example Usage (Agent Mode):
        credential = Credential.objects.get(name='My SERP API')
        tool_fn = SerpApiTool.get_pydantic_tool(credential)
        agent = PydanticAgent(model=llm, toolsets=[tool_fn])

    Example Usage (Workflow Node):
        result = await SerpApiTool.execute(
            credential=my_credential,
            query="What is the weather in London?",
            location="London, UK"
        )
    """

    # Tool metadata
    tool_name = "serp_api"
    display_name = "SERP API Search"
    description = "Search the web using SERP API. Returns organic search results, related questions, and knowledge graph data."
    requires_credential = True
    required_credential_type = "SERP API"
    category = "search"

    # Input schema
    input_schema = {
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "Search query string"
            },
            "location": {
                "type": "string",
                "description": "Geographic location for search results (e.g., 'London, UK', 'New York, US')",
                "default": None
            },
            "num_results": {
                "type": "integer",
                "description": "Number of results to return (1-100)",
                "default": 10,
                "minimum": 1,
                "maximum": 100
            },
            "search_type": {
                "type": "string",
                "description": "Type of search",
                "enum": ["web", "images", "news", "shopping"],
                "default": "web"
            }
        },
        "required": ["query"]
    }

    # Output schema
    output_schema = {
        "type": "object",
        "properties": {
            "organic_results": {
                "type": "array",
                "description": "List of organic search results",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "link": {"type": "string"},
                        "snippet": {"type": "string"},
                        "position": {"type": "integer"}
                    }
                }
            },
            "knowledge_graph": {
                "type": "object",
                "description": "Knowledge graph information if available"
            },
            "related_questions": {
                "type": "array",
                "description": "Related questions/searches"
            },
            "search_metadata": {
                "type": "object",
                "description": "Metadata about the search"
            }
        }
    }

    @classmethod
    async def execute(
        cls,
        credential: Optional[Credential],
        query: str,
        location: Optional[str] = None,
        num_results: int = 10,
        search_type: str = "web"
    ) -> Dict[str, Any]:
        """
        Execute SERP API search.

        Args:
            credential: Credential containing SERP API key
            query: Search query string
            location: Geographic location for results
            num_results: Number of results to return (1-100)
            search_type: Type of search (web, images, news, shopping)

        Returns:
            dict: Search results with organic_results, knowledge_graph, etc.

        Raises:
            ValueError: If credential is missing or invalid
            httpx.HTTPError: If API request fails
        """
        # Validate credential
        if not credential:
            raise ValueError("SERP API credential is required")

        # Get API key from credential (wrap Django ORM call in sync_to_async)
        connection_details = await sync_to_async(credential.get_connection_details)()
        api_key = connection_details.get('api_key') or connection_details.get('API Key')

        if not api_key:
            raise ValueError(
                f"API key not found in credential. Available fields: {list(connection_details.keys())}"
            )

        # Validate inputs
        cls.validate_inputs({
            'query': query,
            'location': location,
            'num_results': num_results,
            'search_type': search_type
        })

        # Build request parameters
        params = {
            "q": query,
            "api_key": api_key,
            "engine": "google",  # Default to Google search
            "num": num_results,
        }

        if location:
            params["location"] = location

        # Handle different search types
        if search_type == "images":
            params["tbm"] = "isch"
        elif search_type == "news":
            params["tbm"] = "nws"
        elif search_type == "shopping":
            params["tbm"] = "shop"

        # Make API request
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://serpapi.com/search",
                    params=params
                )
                response.raise_for_status()
                data = response.json()

            # Extract and format results
            result = {
                "organic_results": cls._format_organic_results(data.get("organic_results", [])),
                "knowledge_graph": data.get("knowledge_graph"),
                "related_questions": data.get("related_questions", []),
                "search_metadata": {
                    "query": query,
                    "location": location,
                    "total_results": data.get("search_information", {}).get("total_results"),
                    "time_taken": data.get("search_information", {}).get("time_taken_displayed"),
                }
            }

            return result

        except httpx.HTTPError as e:
            raise Exception(f"SERP API request failed: {str(e)}")

    @classmethod
    def _format_organic_results(cls, results: List[Dict]) -> List[Dict]:
        """
        Format organic search results to consistent structure.

        Args:
            results: Raw organic results from SERP API

        Returns:
            list: Formatted results
        """
        formatted = []
        for result in results:
            formatted.append({
                "title": result.get("title", ""),
                "link": result.get("link", ""),
                "snippet": result.get("snippet", ""),
                "position": result.get("position", 0),
                "displayed_link": result.get("displayed_link", ""),
            })
        return formatted

    @classmethod
    def get_pydantic_tool(cls, credential: Optional[Credential]):
        """
        Create PydanticAI compatible tool function.

        The credential is captured in closure and not exposed to LLM.

        Args:
            credential: SERP API credential

        Returns:
            Callable: PydanticAI tool function
        """
        async def serp_api(
            query: str,
            location: Optional[str] = None,
            num_results: int = 10,
            search_type: str = "web"
        ) -> Dict[str, Any]:
            """Search the web using SERP API. Returns search results with titles, links, and snippets."""
            # Credential is injected via closure - NOT visible to LLM!
            return await cls.execute(
                credential=credential,
                query=query,
                location=location,
                num_results=num_results,
                search_type=search_type
            )

        return serp_api
