"""
Simplified Workflow Builder Chat Service

A basic conversational service with session management, designed for frontend integration.
No workflow building logic - just simple chat capabilities with message persistence.
"""

import os
import json
from typing import List, Dict, Any
from datetime import datetime, timezone

import fastapi
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

import aiosqlite
from dotenv import load_dotenv

import httpx
from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.messages import (
    ModelMessage,
    ModelMessagesTypeAdapter,
    ModelRequest,
    ModelResponse,
    TextPart,
    UserPromptPart,
)
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

# Import structured response models
from models import (
    ConversationalResponse, NodeAddAction, EdgeAddAction, NodeRemoveAction, EdgeRemoveAction,
    NodeConfig, NodePosition, CredentialInfo, AgentInfo, AgentDetailInfo, SchemaInspectionResult, DatabaseQueryResult
)


# Load environment variables
load_dotenv()


# ============================================================================
# Configuration
# ============================================================================

DB_PATH = os.getenv("DB_PATH", "messages.db")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash-latest")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
DJANGO_API_BASE = os.getenv("DJANGO_API_BASE", "http://localhost:8000")

if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set. Please set your Google API key in the .env file.")

# Initialize Gemini model
provider = GoogleProvider(api_key=GOOGLE_API_KEY)
model = GoogleModel(MODEL_NAME, provider=provider)


# ============================================================================
# Simple Chat Agent
# ============================================================================

AGENT_PROMPT = """
You are a workflow builder assistant that helps users create workflows through conversation.

You have access to TOOLS that let you query Django API for available resources:
- get_credentials(search="", category="RDBMS") - Find database credentials
- get_agents(search="") - Find AI agents (basic list)
- get_agent_details(agent_id) - Get detailed agent info (prompts, tools, capabilities)
- inspect_database_schema(credential_id) - Get database schema info
- query_database(credential_id, query) - Test SQL queries (auto-limited to 1 row)

You can handle THREE types of interactions:

1. **CONVERSATIONAL**: When user is chatting, asking questions, greeting, or seeking help
   - Return ConversationalResponse with a friendly message
   - Be helpful, concise, and guide them
   - Use tools to answer questions about available resources

   Examples:
   - "what agents are available?" → Call get_agents(search="") → Return list in conversational message
   - "what databases can I use?" → Call get_credentials(search="", category="RDBMS") → Return list
   - "tell me about the customer database" → Call get_credentials() → Find match → Maybe call inspect_database_schema()

2. **NODE ADD REQUEST**: When user explicitly asks to add a workflow node
   - Detect the node type they want
   - Use tools to find appropriate resources (credentials, agents, etc.)
   - Generate appropriate configuration with pre-filled IDs
   - Return NodeAddAction with the node details

   Examples:
   - "add a database node" → Call get_credentials() → Use first credential_id in config
   - "add agent node" → Call get_agents() → Use first agent_id in config

3. **WORKFLOW ACTIONS**: Node/edge manipulation (add, remove, connect)
   - Covered in detail below

TOOL USAGE GUIDELINES:
- ALWAYS call get_credentials(search="") and get_agents(search="") with EMPTY search=""
- This returns ALL available resources, letting you intelligently choose the best match
- When user asks "what agents?" → Call get_agents() → Return friendly list in ConversationalResponse
- When user asks about SPECIFIC agent abilities/capabilities → Call get_agent_details(agent_id) → Return detailed info
- When adding nodes, call tools proactively to pre-fill configs with real IDs
- Use inspect_database_schema() to get actual table/column names for SQL queries
- Use query_database() sparingly - only to validate or understand data patterns

DETAILED AGENT QUERIES:
When user asks about a specific agent's abilities, capabilities, or what it does:
1. Find the agent_id from previous conversation (e.g., from get_agents() results)
2. Call get_agent_details(agent_id) to fetch complete information
3. Return ConversationalResponse with formatted details about prompts, tools, and capabilities

Examples:
  User: "what agents are available?"
  You: [Call get_agents()] → Return list in ConversationalResponse

  User: "what are the abilities of data analyst agent?" or "tell me about agent ID 9"
  You: [Extract agent_id=9] → [Call get_agent_details(9)] → Return detailed capabilities in ConversationalResponse

  User: "what does the text classifier do?"
  You: [Find agent_id from previous context] → [Call get_agent_details(id)] → Return detailed info

AVAILABLE NODE TYPES:
- trigger_manual: Manual workflow trigger (button/API)
- trigger_schedule: Scheduled workflow (cron-based)
- trigger_chat: Chat-triggered workflow
- database: SQL database query node
- agent: AI agent processing node
- toolbox: Tool attachment node
- filter: Data filtering node
- script: Custom Python/JavaScript code
- conditional: Branch logic node
- output: Save results (database/file)

NODE POSITIONING:
- ALWAYS check the current workflow state to calculate position
- Formula: x = 100 + (current_node_count * 300)
- Examples:
  - 0 nodes → x=100 (first node)
  - 1 node → x=400 (second node)
  - 2 nodes → x=700 (third node)
- Keep y=200 for simple horizontal layout

NODE ID NAMING:
- Format: {node_type}-{number} (e.g., "trigger-1", "database-1", "agent-1")
- Check existing nodes to increment number correctly
- If "database-1" exists, next should be "database-2"

WORKFLOW STATE AWARENESS:
- You will receive the current workflow state showing existing nodes
- Use this to calculate proper positions and avoid duplicates
- If user asks for duplicate node type, warn them but still add if confirmed
- Suggest logical next steps based on what's already in the workflow

EDGE CREATION (CONNECTING NODES):
When user says "connect X to Y", "join X to Y", or "link X to Y":
1. Check the workflow state to verify both nodes exist
2. Find the EXACT node IDs from the workflow state (e.g., "node-1760699375211-qu9uiwd2a")
3. Identify the node types from the workflow state
4. Determine the correct handles based on node types and user intent
5. Return EdgeAddAction using the EXACT node IDs from workflow state

CRITICAL: ALWAYS use the EXACT node IDs from the current workflow state
- DO NOT use friendly names like "trigger-1" or "agent-1"
- DO NOT invent new IDs
- Use the complete ID as shown in workflow state (e.g., "node-1234567890-abc123")

HANDLE DETERMINATION RULES:
- **Agent node** has 3 input handles:
  * data-input (left top, blue) - Main data flow, SINGLE connection
  * context-input (left bottom, orange) - Additional context, MULTIPLE connections allowed
  * tools-input (bottom, amber) - ONLY for toolbox nodes, SINGLE connection

- **Default behavior** when connecting TO an agent:
  * If user says "connect X to agent-Y" → use target_handle="data-input"
  * If user mentions "context" → use target_handle="context-input"
  * If source is toolbox node type → MUST use target_handle="tools-input"

- **Toolbox node** rules:
  * Can ONLY connect to agent nodes
  * MUST use target_handle="tools-input"
  * One toolbox per agent maximum

- **Conditional node** has 2 output handles:
  * source_handle="true" for true branch
  * source_handle="false" for false branch

- **All other nodes** (trigger_*, database, output, filter, script):
  * Use source_handle=None and target_handle=None (default connections)

EDGE CREATION EXAMPLES:

Input: "connect the trigger to the agent"
Workflow state:
  - node "node-1234567890-abc" (type: trigger_chat) exists
  - node "node-9876543210-xyz" (type: agent) exists
Output: EdgeAddAction(
    source_node_id="node-1234567890-abc",  # Use EXACT ID from workflow state
    target_node_id="node-9876543210-xyz",  # Use EXACT ID from workflow state
    source_handle=None,
    target_handle="data-input",
    message="✅ Connected trigger to agent (data input)"
)

Input: "connect database to agent context"
Workflow state:
  - node "node-1111111111-aaa" (type: database) exists
  - node "node-2222222222-bbb" (type: agent) exists
Output: EdgeAddAction(
    source_node_id="node-1111111111-aaa",
    target_node_id="node-2222222222-bbb",
    source_handle=None,
    target_handle="context-input",
    message="✅ Connected database to agent (context input)"
)

Input: "connect toolbox to agent"
Workflow state:
  - node "node-3333333333-ccc" (type: toolbox) exists
  - node "node-4444444444-ddd" (type: agent) exists
Output: EdgeAddAction(
    source_node_id="node-3333333333-ccc",
    target_node_id="node-4444444444-ddd",
    source_handle=None,
    target_handle="tools-input",
    message="✅ Connected toolbox to agent (tools input)"
)

Input: "connect trigger to database"
Workflow state:
  - node "node-5555555555-eee" (type: trigger_manual) exists
  - node "node-6666666666-fff" (type: database) exists
Output: EdgeAddAction(
    source_node_id="node-5555555555-eee",
    target_node_id="node-6666666666-fff",
    source_handle=None,
    target_handle=None,
    message="✅ Connected trigger to database"
)

NODE REMOVAL:
When user says "remove node X", "delete the trigger", "remove the agent":
1. Find the node in workflow state by type (look for trigger_*, agent, database, etc.)
2. Get the EXACT node ID from workflow state
3. Return NodeRemoveAction with the exact ID

Examples:

Input: "remove the trigger"
Workflow state: node "node-1234567890-abc" (type: trigger_chat) exists
Output: NodeRemoveAction(
    node_id="node-1234567890-abc",
    message="✅ Removed trigger node"
)

Input: "delete the agent node"
Workflow state: node "node-9876543210-xyz" (type: agent) exists
Output: NodeRemoveAction(
    node_id="node-9876543210-xyz",
    message="✅ Removed agent node"
)

EDGE REMOVAL:
When user says "remove edge between X and Y", "disconnect X from Y", "delete the connection":
1. Find both nodes in workflow state by their types
2. Look through edges array to find the edge connecting them (check source and target)
3. Get the source node ID, target node ID, and handles (targetHandle, sourceHandle)
4. Return EdgeRemoveAction with source_node_id, target_node_id, and handles

IMPORTANT: Return the node IDs and handles, NOT the edge ID!

Examples:

Input: "disconnect trigger from agent"
Workflow state:
  - node "node-111-aaa" (type: trigger_chat)
  - node "node-222-bbb" (type: agent)
  - edge has source="node-111-aaa", target="node-222-bbb", targetHandle="data-input"
Output: EdgeRemoveAction(
    source_node_id="node-111-aaa",
    target_node_id="node-222-bbb",
    source_handle=None,
    target_handle="data-input",
    message="✅ Disconnected trigger from agent"
)

Input: "remove the edge between database and agent context"
Workflow state:
  - node "node-333-ccc" (type: database)
  - node "node-444-ddd" (type: agent)
  - edge has source="node-333-ccc", target="node-444-ddd", targetHandle="context-input"
Output: EdgeRemoveAction(
    source_node_id="node-333-ccc",
    target_node_id="node-444-ddd",
    source_handle=None,
    target_handle="context-input",
    message="✅ Removed edge between database and agent (context)"
)

NODE CREATION EXAMPLES:

Input: "hello"
Output: ConversationalResponse(
    message="Hello! I'm your workflow builder assistant. I can help you create workflows by adding nodes. Just tell me what you need, like 'I need a manual trigger' or 'add a database node'."
)

Input: "I need a manual trigger"
Output: NodeAddAction(
    node_id="trigger-1",
    node=NodeConfig(
        node_type="trigger_manual",
        position=NodePosition(x=100, y=200),
        config={},
        label="Manual Trigger"
    ),
    message="✅ Added manual trigger node! This lets you start the workflow manually via button or API."
)

Input: "add a database node"
Output: NodeAddAction(
    node_id="database-1",
    node=NodeConfig(
        node_type="database",
        position=NodePosition(x=400, y=200),
        config={"credential_id": None, "query": "SELECT * FROM table", "placeholders": {}},
        label="Database"
    ),
    message="✅ Added database node! Configure the database connection and SQL query in the node settings."
)

Input: "thanks!"
Output: ConversationalResponse(
    message="You're welcome! Need anything else? I can add more nodes or answer questions about workflows."
)

Input: "I need an AI agent"
Output: NodeAddAction(
    node_id="agent-1",
    node=NodeConfig(
        node_type="agent",
        position=NodePosition(x=700, y=200),
        config={"agent_id": None, "llm_credential_id": None, "batch_size": 100, "timeout": 30},
        label="AI Agent"
    ),
    message="✅ Added AI agent node! Select an agent and LLM credential in the node settings."
)

REMEMBER:
- **Questions about resources**: Use tools (get_credentials, get_agents) then return ConversationalResponse with list
- **Node creation**: if user says "add", "need", "create" + node name = NodeAddAction (optionally call tools first to pre-fill IDs)
- **Edge creation**: if user says "connect", "join", "link" + node IDs = EdgeAddAction
- **Node removal**: if user says "remove", "delete" + node type = NodeRemoveAction
- **Edge removal**: if user says "disconnect", "remove edge", "delete connection" = EdgeRemoveAction
- **Conversation**: Otherwise = ConversationalResponse
- Keep messages friendly and concise
- Provide helpful guidance
- Always check workflow state before operations to verify nodes/edges exist
- ALWAYS use exact IDs from workflow state, never invent IDs
- Use tools to provide intelligent, context-aware responses about available resources
"""

# Create agent with structured output
chat_agent = Agent(
    model,
    deps_type=str,  # session_id passed as dependency for tools
    output_type=ConversationalResponse | NodeAddAction | EdgeAddAction | NodeRemoveAction | EdgeRemoveAction,
    instructions=AGENT_PROMPT,
)

print(f"\n{'*'*80}")
print(f"🤖 WORKFLOW BUILDER AGENT INITIALIZED")
print(f"   Model: {MODEL_NAME}")
print(f"   Output: ConversationalResponse | NodeAddAction | EdgeAddAction | NodeRemoveAction | EdgeRemoveAction")
print(f"   Mode: Intent-based routing (conversation + node/edge add/remove)")
print(f"   Tools: get_credentials, get_agents, get_agent_details, inspect_database_schema, query_database")
print(f"{'*'*80}\n")


# ============================================================================
# Agent Tools - Django API Integration
# ============================================================================

@chat_agent.tool
async def get_credentials(ctx: RunContext[str], search: str = "", category: str = "RDBMS") -> str:
    """
    Get available database credentials for the current user.

    Args:
        search: Optional search term (usually empty to get all)
        category: Credential category (default: RDBMS)

    Returns:
        Formatted string with credentials list
    """
    session_id = ctx.deps

    print(f"\n{'='*80}")
    print(f"🔧 TOOL: get_credentials")
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

            if credentials:
                cred_list = "\n".join(
                    f"  • {c.name} (ID: {c.id}) - {c.credential_type_name}" +
                    (f" - {c.description}" if c.description else "")
                    for c in credentials
                )
                result = f"Found {len(credentials)} credential(s):\n{cred_list}"
            else:
                result = "No credentials found."

            print(f"✅ get_credentials SUCCESS: {len(credentials)} credentials found")
            return result

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"❌ get_credentials ERROR: {error_msg}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error fetching credentials: {e.response.status_code}")
        return f"Error fetching credentials: {error_msg}"
    except Exception as e:
        error_msg = str(e)
        print(f"❌ get_credentials EXCEPTION: {error_msg}")
        return f"Tool execution failed: {error_msg}"


@chat_agent.tool
async def get_agents(ctx: RunContext[str], search: str = "") -> str:
    """
    Get available AI agents for the current project.

    Args:
        search: Optional search term (usually empty to get all)

    Returns:
        Formatted string with agents list
    """
    session_id = ctx.deps

    print(f"\n{'='*80}")
    print(f"🔧 TOOL: get_agents")
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

            if agents:
                agent_list = "\n".join(
                    f"  • {a.name} (ID: {a.id})" +
                    (f" - {a.description}" if a.description else "") +
                    (f" [Return type: {a.return_type}]" if a.return_type else "")
                    for a in agents
                )
                result = f"Found {len(agents)} agent(s):\n{agent_list}"
            else:
                result = "No agents found."

            print(f"✅ get_agents SUCCESS: {len(agents)} agents found")
            return result

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"❌ get_agents ERROR: {error_msg}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error fetching agents: {e.response.status_code}")
        return f"Error fetching agents: {error_msg}"
    except Exception as e:
        error_msg = str(e)
        print(f"❌ get_agents EXCEPTION: {error_msg}")
        return f"Tool execution failed: {error_msg}"


@chat_agent.tool
async def get_agent_details(ctx: RunContext[str], agent_id: int) -> str:
    """
    Get detailed information about a specific agent including prompts, tools, and capabilities.

    Use this when user asks about an agent's abilities, capabilities, or what it does.

    Args:
        agent_id: ID of the agent to get details for

    Returns:
        Formatted string with agent details
    """
    session_id = ctx.deps

    print(f"\n{'='*80}")
    print(f"🔧 TOOL: get_agent_details")
    print(f"   Session ID: {session_id}")
    print(f"   Agent ID: {agent_id}")
    print(f"{'='*80}\n")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{DJANGO_API_BASE}/api/builder-tools/get_agent_details/"
            params = {"session_id": session_id, "agent_id": agent_id}

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            # Format detailed response
            result = f"Agent: {data['name']} (ID: {agent_id})\n"
            result += f"Type: {data.get('return_type', 'unstructured')}\n"

            if data.get('description'):
                result += f"Description: {data['description']}\n"

            # Prompts
            prompts = data.get('prompts', [])
            if prompts:
                result += f"\nPrompts ({len(prompts)}):\n"
                for p in prompts:
                    prompt_content = p.get('content', '')
                    # Truncate long prompts
                    if len(prompt_content) > 200:
                        prompt_content = prompt_content[:200] + "..."
                    result += f"  • {p.get('prompt_type', 'unknown')}: {prompt_content}\n"

            # Tools
            agent_tools = data.get('agent_tools', [])
            if agent_tools:
                result += f"\nTools ({len(agent_tools)}):\n"
                for t in agent_tools:
                    tool_name = t.get('tool_name', 'unknown')
                    tool_type = t.get('tool_type', 'unknown')
                    result += f"  • {tool_name} ({tool_type})\n"

            # MCP Servers
            mcp_servers = data.get('mcp_servers', [])
            if mcp_servers:
                result += f"\nMCP Servers ({len(mcp_servers)}):\n"
                for mcp in mcp_servers:
                    result += f"  • {mcp.get('name', 'unknown')}\n"

            # Internal Tools
            internal_tools = data.get('internal_tools', [])
            if internal_tools:
                result += f"\nInternal Tools ({len(internal_tools)}):\n"
                for it in internal_tools:
                    result += f"  • {it.get('name', 'unknown')} - {it.get('description', '')}\n"

            # Input placeholders
            input_placeholders = data.get('input_placeholders', [])
            if input_placeholders:
                result += f"\nRequired inputs: {', '.join(input_placeholders)}\n"

            # Schema definition for structured agents
            schema_def = data.get('schema_definition')
            if schema_def:
                result += f"\nOutput Schema: {schema_def}\n"

            print(f"✅ get_agent_details SUCCESS: Retrieved details for agent {agent_id}")
            return result

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"❌ get_agent_details ERROR: {error_msg}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error fetching agent details: {e.response.status_code}")
        return f"Error fetching agent details: {error_msg}"
    except Exception as e:
        error_msg = str(e)
        print(f"❌ get_agent_details EXCEPTION: {error_msg}")
        return f"Tool execution failed: {error_msg}"


@chat_agent.tool
async def inspect_database_schema(ctx: RunContext[str], credential_id: int) -> str:
    """
    Inspect database schema for a credential.

    Args:
        credential_id: ID of the database credential

    Returns:
        Formatted string with schema information
    """
    session_id = ctx.deps

    print(f"\n{'='*80}")
    print(f"🔧 TOOL: inspect_database_schema")
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

            # Format schema info
            tables = data.get("metadata", {}).get("tables", [])
            table_info = []
            for table in tables[:5]:  # Show first 5 tables
                table_name = table.get("name", "unknown")
                columns = table.get("columns", [])
                col_list = ", ".join(c.get("name", "?") for c in columns[:5])
                if len(columns) > 5:
                    col_list += f" ... ({len(columns)} total)"
                table_info.append(f"  • {table_name}: {col_list}")

            table_summary = "\n".join(table_info)
            if len(tables) > 5:
                table_summary += f"\n  ... and {len(tables) - 5} more tables"

            result = (
                f"Database: {data['credential_name']} ({data['database_type']})\n"
                f"Tables ({len(tables)} total):\n{table_summary}\n"
                f"Use credential_id={credential_id} in database node config."
            )

            print(f"✅ inspect_database_schema SUCCESS: {len(tables)} tables found")
            return result

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"❌ inspect_database_schema ERROR: {error_msg}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error inspecting schema: {e.response.status_code}")
        return f"Error inspecting schema: {error_msg}"
    except Exception as e:
        error_msg = str(e)
        print(f"❌ inspect_database_schema EXCEPTION: {error_msg}")
        return f"Tool execution failed: {error_msg}"


@chat_agent.tool
async def query_database(ctx: RunContext[str], credential_id: int, query: str) -> str:
    """
    Execute a SQL query to analyze data.

    Query is automatically limited to 1 row for safety.

    Args:
        credential_id: ID of the database credential
        query: SQL query to execute

    Returns:
        Formatted string with query results
    """
    session_id = ctx.deps

    print(f"\n{'='*80}")
    print(f"🔧 TOOL: query_database")
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

            # Format result
            columns = data.get("columns", [])
            rows = data.get("data", [])
            row_count = data.get("row_count", 0)

            result = f"Query executed: {row_count} row(s), {len(columns)} column(s)\n"
            if columns:
                result += f"Columns: {', '.join(columns)}\n"
            if rows:
                result += f"Sample data: {rows[0]}"

            print(f"✅ query_database SUCCESS: {row_count} rows returned")
            return result

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"❌ query_database ERROR: {error_msg}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error executing query: {e.response.status_code}")
        return f"Error executing query: {error_msg}"
    except Exception as e:
        error_msg = str(e)
        print(f"❌ query_database EXCEPTION: {error_msg}")
        return f"Tool execution failed: {error_msg}"


# ============================================================================
# SQLite Message Persistence
# ============================================================================

CREATE_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  session_id TEXT NOT NULL,
  blob BLOB NOT NULL
);
"""

CREATE_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_messages_session_id ON messages(session_id);"

INSERT_SQL = "INSERT INTO messages (created_at, session_id, blob) VALUES (?, ?, ?);"
SELECT_BY_SESSION_SQL = "SELECT blob FROM messages WHERE session_id = ? ORDER BY id ASC;"
DELETE_BY_SESSION_SQL = "DELETE FROM messages WHERE session_id = ?;"


async def add_messages_blob(session_id: str, blob: bytes) -> None:
    """Add message blob to database for a session."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(INSERT_SQL, (datetime.now(timezone.utc).isoformat(), session_id, blob))
        await db.commit()


async def load_messages(session_id: str) -> List[ModelMessage]:
    """Load all messages for a session from database."""
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(SELECT_BY_SESSION_SQL, (session_id,))
        rows = await cur.fetchall()

    messages: List[ModelMessage] = []
    for (blob,) in rows:
        messages.extend(ModelMessagesTypeAdapter.validate_json(blob))
    return messages


async def reset_messages(session_id: str) -> None:
    """Clear all messages for a session."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(DELETE_BY_SESSION_SQL, (session_id,))
        await db.commit()


# ============================================================================
# Session Storage (In-Memory)
# ============================================================================

SESSION_STORAGE: Dict[str, Dict[str, Any]] = {}


async def store_session_context(session_id: str) -> None:
    """Store minimal session context - just usage tracking."""
    SESSION_STORAGE[session_id] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "usage": {
            "requests": 0,
            "request_tokens": 0,
            "response_tokens": 0,
            "total_tokens": 0
        }
    }


async def update_session_usage(session_id: str, requests: int, request_tokens: int, response_tokens: int, total_tokens: int) -> None:
    """Update session usage statistics."""
    if session_id in SESSION_STORAGE:
        usage = SESSION_STORAGE[session_id]["usage"]
        usage["requests"] += requests
        usage["request_tokens"] += request_tokens
        usage["response_tokens"] += response_tokens
        usage["total_tokens"] += total_tokens


# ============================================================================
# API Models
# ============================================================================

class GenerateRequest(BaseModel):
    """Request to generate a chat response."""
    prompt: str
    session_id: str
    current_workflow: dict | None = None  # Current workflow state from canvas


class SessionScopedRequest(BaseModel):
    """Request with session_id."""
    session_id: str


class NewSessionRequest(BaseModel):
    """Request to create a new session (session_id from Django)."""
    session_id: str


class NewSessionResponse(BaseModel):
    """Response with session_id."""
    session_id: str
    status: str


# ============================================================================
# FastAPI App
# ============================================================================

app = fastapi.FastAPI(title="Workflow Chat Service (Simplified)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup() -> None:
    """Initialize database on startup."""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.execute(CREATE_INDEX_SQL)
        await db.commit()
    print("✅ Database initialized")


# ============================================================================
# Utilities
# ============================================================================

def now_iso() -> str:
    """Get current timestamp in ISO format."""
    return datetime.now(tz=timezone.utc).isoformat()


# ============================================================================
# API Routes
# ============================================================================

@app.get("/healthz")
async def healthz() -> Response:
    """Health check endpoint."""
    return Response("ok", media_type="text/plain")


@app.post("/session/", response_model=NewSessionResponse)
async def new_session(body: NewSessionRequest) -> NewSessionResponse:
    """
    Initialize a new chat session.

    The session_id is provided by Django backend.
    """
    session_id = body.session_id
    await store_session_context(session_id)

    print(f"\n📝 New session initialized: {session_id}")

    return NewSessionResponse(session_id=session_id, status="initialized")


@app.post("/generate/")
async def generate_chat(body: GenerateRequest) -> StreamingResponse:
    """
    Generate streaming chat responses with structured output.

    Handles both conversational responses and node add actions.
    """
    prompt = body.prompt
    session_id = body.session_id
    current_workflow = body.current_workflow

    print(f"\n💬 Chat request - Session: {session_id}")
    print(f"   Prompt: {prompt[:80]}{'...' if len(prompt) > 80 else ''}")

    # Format workflow state context
    workflow_context = ""
    if current_workflow and current_workflow.get("nodes"):
        nodes = current_workflow["nodes"]
        print(f"   Current workflow: {len(nodes)} nodes")

        workflow_context = f"\n\nCURRENT WORKFLOW STATE:\n"
        workflow_context += f"Total nodes: {len(nodes)}\n"
        workflow_context += "Existing nodes:\n"
        for node in nodes:
            workflow_context += f"  - {node.get('id')} ({node.get('type')}) at x={node.get('position', {}).get('x', 0)}\n"
        workflow_context += f"\nNext node should be positioned at x={100 + (len(nodes) * 300)}, y=200\n"
    else:
        print(f"   Current workflow: empty (starting fresh)")
        workflow_context = "\n\nCURRENT WORKFLOW STATE: Empty (no nodes yet)\nNext node should be positioned at x=100, y=200\n"

    # Augment user prompt with workflow context
    augmented_prompt = f"{workflow_context}\nUSER REQUEST: {prompt}"

    async def stream():
        # Echo user message
        yield json.dumps({
            "role": "user",
            "timestamp": now_iso(),
            "content": prompt
        }).encode("utf-8") + b"\n"

        # Load message history
        messages = await load_messages(session_id)
        print(f"   Loaded {len(messages)} messages from history")

        # Run chat agent with structured output (using augmented prompt with workflow context)
        # Pass session_id as deps for tool access
        result = await chat_agent.run(augmented_prompt, message_history=messages, deps=session_id)
        output = result.output

        # Determine output type and stream appropriate response
        if isinstance(output, NodeAddAction):
            # Node add action
            print(f"   🎯 Intent: NODE_ADD ({output.node.node_type})")

            yield json.dumps({
                "role": "assistant",
                "timestamp": now_iso(),
                "content": output.message,
                "action": "node_add",
                "data": {
                    "node_id": output.node_id,
                    "type": output.node.node_type,
                    "position": {
                        "x": output.node.position.x,
                        "y": output.node.position.y
                    },
                    "config": output.node.config,
                    "label": output.node.label
                }
            }).encode("utf-8") + b"\n"

        elif isinstance(output, EdgeAddAction):
            # Edge add action
            print(f"   🔗 Intent: EDGE_ADD ({output.source_node_id} → {output.target_node_id})")
            print(f"      Handles: source={output.source_handle}, target={output.target_handle}")

            yield json.dumps({
                "role": "assistant",
                "timestamp": now_iso(),
                "content": output.message,
                "action": "edge_add",
                "data": {
                    "source_node_id": output.source_node_id,
                    "target_node_id": output.target_node_id,
                    "source_handle": output.source_handle,
                    "target_handle": output.target_handle
                }
            }).encode("utf-8") + b"\n"

        elif isinstance(output, NodeRemoveAction):
            # Node remove action
            print(f"   🗑️ Intent: NODE_REMOVE ({output.node_id})")

            yield json.dumps({
                "role": "assistant",
                "timestamp": now_iso(),
                "content": output.message,
                "action": "node_remove",
                "data": {
                    "node_id": output.node_id
                }
            }).encode("utf-8") + b"\n"

        elif isinstance(output, EdgeRemoveAction):
            # Edge remove action
            print(f"   ✂️ Intent: EDGE_REMOVE ({output.edge_id})")

            yield json.dumps({
                "role": "assistant",
                "timestamp": now_iso(),
                "content": output.message,
                "action": "edge_remove",
                "data": {
                    "edge_id": output.edge_id
                }
            }).encode("utf-8") + b"\n"

        elif isinstance(output, ConversationalResponse):
            # Conversational response
            print(f"   💬 Intent: CONVERSATIONAL")

            yield json.dumps({
                "role": "assistant",
                "timestamp": now_iso(),
                "content": output.message
            }).encode("utf-8") + b"\n"

        # Persist new messages
        await add_messages_blob(session_id, result.new_messages_json())
        print(f"   ✅ Response sent and persisted")

        # Track usage
        usage = result.usage()
        await update_session_usage(
            session_id,
            requests=usage.requests,
            request_tokens=usage.request_tokens,
            response_tokens=usage.response_tokens,
            total_tokens=usage.total_tokens
        )

    return StreamingResponse(stream(), media_type="text/plain")


@app.get("/generate/finalize/")
async def generate_finalize(session_id: str) -> Response:
    """
    Finalize endpoint (placeholder).

    Returns 202 status indicating feature not implemented yet.
    This endpoint will be used later for workflow finalization.
    """
    print(f"\n📋 Finalize called for session: {session_id}")
    print(f"   Status: Not implemented (placeholder)")

    return Response(
        "Not implemented yet. This endpoint will be used for workflow finalization.",
        media_type="text/plain",
        status_code=202
    )


@app.post("/reset/")
async def reset(body: SessionScopedRequest) -> Response:
    """Reset conversation for a session."""
    session_id = body.session_id
    await reset_messages(session_id)

    print(f"\n🔄 Reset session: {session_id}")

    return Response("OK", media_type="text/plain")


@app.get("/")
async def index() -> Response:
    """Root endpoint."""
    return Response("Workflow Chat Service (Simplified)", media_type="text/plain")
