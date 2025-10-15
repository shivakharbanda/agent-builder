"""
Worker Agent - Tool Execution

This agent executes tools autonomously without asking for user permission.
It has access to all 4 workflow builder tools and reports results back to the supervisor.
"""

import os
from datetime import datetime, timezone
from typing import List

import httpx
from pydantic import BaseModel
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from models.responses import WorkerToolResult
from models.deps import WorkerDeps


# ============================================================================
# Tool Result Models (from app.py)
# ============================================================================

class CredentialInfo(BaseModel):
    """Database credential information"""
    id: int
    name: str
    credential_type_name: str
    description: str | None = None
    credential_type_category: str | None = None
    details_count: int | None = None
    created_at: str | None = None
    is_active: bool | None = None


class AgentInfo(BaseModel):
    """AI agent information"""
    id: int
    name: str
    description: str | None = None
    return_type: str | None = None
    project_name: str | None = None
    prompts_count: int | None = None
    tools_count: int | None = None
    created_at: str | None = None
    is_active: bool | None = None


class SchemaInspectionResult(BaseModel):
    """Schema inspection result"""
    credential_id: int
    credential_name: str
    database_type: str
    metadata: dict  # DataSourceMetadata as dict


class DatabaseQueryResult(BaseModel):
    """Database query execution result"""
    columns: List[str]
    data: List[dict]
    row_count: int


# ============================================================================
# Worker Agent Configuration
# ============================================================================

DJANGO_API_BASE = os.getenv("DJANGO_API_BASE", "http://localhost:8000")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash-latest")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set")

provider = GoogleProvider(api_key=GOOGLE_API_KEY)
model = GoogleModel(MODEL_NAME, provider=provider)


# ============================================================================
# Worker Agent Prompt
# ============================================================================

WORKER_PROMPT = """
You are a workflow builder tool executor.

Your role is to EXECUTE TOOLS AUTONOMOUSLY and report results back to your supervisor.

AVAILABLE TOOLS:
1. get_credentials(search="", category="RDBMS") - Find database credentials
2. get_agents(search="") - Find AI agents
3. inspect_database_schema(credential_id) - Get database schema (tables, columns, sample data)
4. query_database(credential_id, query) - Execute SQL queries (auto-limited to 1 row)

EXECUTION PRINCIPLES:
- Execute tools WITHOUT asking for permission
- Be thorough - gather complete context
- Report results concisely to supervisor
- Handle errors gracefully and report them

TOOL USAGE STRATEGY:

When asked to find credentials:
- ALWAYS call get_credentials(search="") with EMPTY search to fetch ALL credentials
- The supervisor will choose the best match
- Include credential names, types, and descriptions in your report

When asked to find agents:
- ALWAYS call get_agents(search="") with EMPTY search to fetch ALL agents
- Include agent names, descriptions, and return types
- The supervisor will select the appropriate agent

When asked to inspect schema:
- Use credential_id from previous get_credentials() result
- Call inspect_database_schema(credential_id)
- Report table names, column names, and data types
- This gives supervisor info to generate SQL queries

When asked to test queries:
- Call query_database(credential_id, query)
- Report columns and sample data
- Queries are automatically limited to 1 row for safety

EXAMPLES:

Supervisor: "Find database credentials for customer data"
You: [Call get_credentials(search="")]
You: [Return WorkerToolResult with all credentials]

Supervisor: "Inspect the schema for credential 5"
You: [Call inspect_database_schema(credential_id=5)]
You: [Return WorkerToolResult with schema metadata]

REMEMBER:
- NO permission asking - just execute
- Be concise in summaries
- Report all relevant details
- Handle errors and retry if needed
"""

worker_agent = Agent(
    model,
    deps_type=WorkerDeps,
    output_type=WorkerToolResult,
    instructions=WORKER_PROMPT,
)

print(f"\n{'*'*80}")
print(f"🔧 WORKER AGENT INITIALIZED")
print(f"   Model: {MODEL_NAME}")
print(f"   Tools: get_credentials, get_agents, inspect_database_schema, query_database")
print(f"{'*'*80}\n")


# ============================================================================
# Worker Agent Tools
# ============================================================================

@worker_agent.tool
async def get_credentials(ctx: RunContext[WorkerDeps], search: str = "", category: str = "RDBMS") -> WorkerToolResult:
    """
    Get available database credentials for the current user.

    Args:
        search: Optional search term (usually empty to get all)
        category: Credential category (default: RDBMS)

    Returns:
        WorkerToolResult with credentials list
    """
    session_id = ctx.deps.session_id

    print(f"\n{'='*80}")
    print(f"🔧 WORKER TOOL: get_credentials")
    print(f"   Session ID: {session_id}")
    print(f"   Search: '{search}', Category: '{category}'")
    print(f"{'='*80}\n")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{DJANGO_API_BASE}/api/builder-tools/get_credentials/"
            params = {"session_id": session_id, "search": search, "category": category}

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            credentials = [CredentialInfo(**item) for item in data]

            summary = f"Found {len(credentials)} credentials"
            if credentials:
                cred_names = ", ".join(c.name for c in credentials[:3])
                if len(credentials) > 3:
                    cred_names += f" and {len(credentials) - 3} more"
                summary += f": {cred_names}"

            print(f"✅ get_credentials SUCCESS: {summary}")

            return WorkerToolResult(
                success=True,
                tool_name="get_credentials",
                result=[c.model_dump() for c in credentials],
                summary=summary
            )

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"❌ get_credentials ERROR: {error_msg}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error fetching credentials: {e.response.status_code}")
        return WorkerToolResult(
            success=False,
            tool_name="get_credentials",
            result=[],
            summary="No credentials found",
            error=error_msg
        )
    except Exception as e:
        error_msg = str(e)
        print(f"❌ get_credentials EXCEPTION: {error_msg}")
        return WorkerToolResult(
            success=False,
            tool_name="get_credentials",
            result=[],
            summary="Tool execution failed",
            error=error_msg
        )


@worker_agent.tool
async def get_agents(ctx: RunContext[WorkerDeps], search: str = "") -> WorkerToolResult:
    """
    Get available AI agents for the current project.

    Args:
        search: Optional search term (usually empty to get all)

    Returns:
        WorkerToolResult with agents list
    """
    session_id = ctx.deps.session_id

    print(f"\n{'='*80}")
    print(f"🔧 WORKER TOOL: get_agents")
    print(f"   Session ID: {session_id}")
    print(f"   Search: '{search}'")
    print(f"{'='*80}\n")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{DJANGO_API_BASE}/api/builder-tools/get_agents/"
            params = {"session_id": session_id, "search": search}

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            agents = [AgentInfo(**item) for item in data]

            summary = f"Found {len(agents)} agents"
            if agents:
                agent_names = ", ".join(a.name for a in agents[:3])
                if len(agents) > 3:
                    agent_names += f" and {len(agents) - 3} more"
                summary += f": {agent_names}"

            print(f"✅ get_agents SUCCESS: {summary}")

            return WorkerToolResult(
                success=True,
                tool_name="get_agents",
                result=[a.model_dump() for a in agents],
                summary=summary
            )

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"❌ get_agents ERROR: {error_msg}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error fetching agents: {e.response.status_code}")
        return WorkerToolResult(
            success=False,
            tool_name="get_agents",
            result=[],
            summary="No agents found",
            error=error_msg
        )
    except Exception as e:
        error_msg = str(e)
        print(f"❌ get_agents EXCEPTION: {error_msg}")
        return WorkerToolResult(
            success=False,
            tool_name="get_agents",
            result=[],
            summary="Tool execution failed",
            error=error_msg
        )


@worker_agent.tool
async def inspect_database_schema(ctx: RunContext[WorkerDeps], credential_id: int) -> WorkerToolResult:
    """
    Inspect database schema for a credential.

    Args:
        credential_id: ID of the database credential

    Returns:
        WorkerToolResult with schema metadata
    """
    session_id = ctx.deps.session_id

    print(f"\n{'='*80}")
    print(f"🔧 WORKER TOOL: inspect_database_schema")
    print(f"   Session ID: {session_id}")
    print(f"   Credential ID: {credential_id}")
    print(f"{'='*80}\n")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{DJANGO_API_BASE}/api/builder-tools/inspect_schema/"
            json_body = {"credential_id": credential_id, "session_id": session_id}

            response = await client.post(url, json=json_body)
            response.raise_for_status()
            data = response.json()

            # Extract key info for summary
            table_count = len(data.get("metadata", {}).get("tables", []))
            summary = f"Inspected {data['credential_name']} ({data['database_type']}): {table_count} tables"

            print(f"✅ inspect_database_schema SUCCESS: {summary}")

            return WorkerToolResult(
                success=True,
                tool_name="inspect_database_schema",
                result=data,
                summary=summary
            )

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"❌ inspect_database_schema ERROR: {error_msg}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error inspecting schema: {e.response.status_code}")
        return WorkerToolResult(
            success=False,
            tool_name="inspect_database_schema",
            result={},
            summary="Schema inspection failed",
            error=error_msg
        )
    except Exception as e:
        error_msg = str(e)
        print(f"❌ inspect_database_schema EXCEPTION: {error_msg}")
        return WorkerToolResult(
            success=False,
            tool_name="inspect_database_schema",
            result={},
            summary="Tool execution failed",
            error=error_msg
        )


@worker_agent.tool
async def query_database(ctx: RunContext[WorkerDeps], credential_id: int, query: str) -> WorkerToolResult:
    """
    Execute a SQL query to analyze data.

    Query is automatically limited to 1 row for safety.

    Args:
        credential_id: ID of the database credential
        query: SQL query to execute

    Returns:
        WorkerToolResult with query results
    """
    session_id = ctx.deps.session_id

    print(f"\n{'='*80}")
    print(f"🔧 WORKER TOOL: query_database")
    print(f"   Session ID: {session_id}")
    print(f"   Credential ID: {credential_id}")
    print(f"   Query: {query[:100]}...")
    print(f"{'='*80}\n")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{DJANGO_API_BASE}/api/builder-tools/test_query/"
            json_body = {
                "credential_id": credential_id,
                "query": query,
                "session_id": session_id
            }

            response = await client.post(url, json=json_body)
            response.raise_for_status()
            data = response.json()

            summary = f"Query executed: {data['row_count']} rows, {len(data['columns'])} columns"

            print(f"✅ query_database SUCCESS: {summary}")

            return WorkerToolResult(
                success=True,
                tool_name="query_database",
                result=data,
                summary=summary
            )

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"❌ query_database ERROR: {error_msg}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error executing query: {e.response.status_code}")
        return WorkerToolResult(
            success=False,
            tool_name="query_database",
            result={},
            summary="Query execution failed",
            error=error_msg
        )
    except Exception as e:
        error_msg = str(e)
        print(f"❌ query_database EXCEPTION: {error_msg}")
        return WorkerToolResult(
            success=False,
            tool_name="query_database",
            result={},
            summary="Tool execution failed",
            error=error_msg
        )
