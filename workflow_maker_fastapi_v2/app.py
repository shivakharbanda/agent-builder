"""
Simplified Workflow Builder Chat Service

A basic conversational service with session management, designed for frontend integration.
No workflow building logic - just simple chat capabilities with message persistence.
"""

import os
import json
import asyncio
import traceback
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
    AgentNodeUpdateAction, DatabaseNodeUpdateAction, ToolboxNodeUpdateAction,
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

You can handle FOUR types of interactions:

1. **CONVERSATIONAL**: When user is chatting, asking questions, greeting, or seeking help
   - Return ConversationalResponse with a friendly message
   - Be helpful, concise, and guide them
   - Use tools to answer questions about available resources

   Examples:
   - "what agents are available?" → Call get_agents(search="") → Return list in conversational message
   - "what databases can I use?" → Call get_credentials(search="", category="RDBMS") → Return list
   - "tell me about the customer database" → Call get_credentials() → Find match → Maybe call inspect_database_schema()

2. **NODE ADD REQUEST**: When user explicitly asks to ADD/CREATE a NEW workflow node
   - Keywords: "add", "create", "need", "I want"
   - Detect the node type they want
   - Use tools to find appropriate resources (credentials, agents, etc.)
   - Generate appropriate configuration with pre-filled IDs
   - Return NodeAddAction with the node details

   Examples:
   - "add a database node" → Call get_credentials() → Use first credential_id in config
   - "add agent node" → Call get_agents() → Use first agent_id in config

3. **NODE UPDATE REQUEST**: When user wants to CONFIGURE/UPDATE an EXISTING node
   - Keywords: "configure", "update", "set", "change"
   - Check workflow state for existing node type
   - Use tools to find resource IDs
   - Parse JSON from tools to extract numeric IDs
   - Return TYPE-SPECIFIC update action based on node type:
     * Agent nodes → AgentNodeUpdateAction
     * Database nodes → DatabaseNodeUpdateAction
     * Toolbox nodes → ToolboxNodeUpdateAction

   Examples:
   - "configure agent node with data analyst agent" → AgentNodeUpdateAction
   - "update the agent with gemini credential" → AgentNodeUpdateAction
   - "set database credential to postgres" → DatabaseNodeUpdateAction

4. **WORKFLOW ACTIONS**: Node/edge manipulation (add, remove, connect, disconnect)
   - Covered in detail below

TOOL USAGE GUIDELINES:
- ALWAYS call get_credentials(search="") and get_agents(search="") with EMPTY search=""
- This returns ALL available resources for finding exact matches
- When user asks "what agents?" → Call get_agents() → Return friendly list in ConversationalResponse
- When user asks "what tools?" or "what tools do we have?" → Call get_internal_tools() AND get_mcp_servers() → Return categorized list in ConversationalResponse
- When user asks about SPECIFIC agent abilities/capabilities → Call get_agent_details(agent_id) → Return detailed info
- Use inspect_database_schema() to get actual table/column names for SQL queries
- Use query_database() sparingly - only to validate or understand data patterns

EXPLICIT AGENT NODE CONFIGURATION:

When user says "add agent node" with specifications, parse the command for:
- Agent name (e.g., "using data analyst agent", "with text classifier")
- Credential name (e.g., "with gemini credential", "using openai")
- Model name (e.g., "model gemini-2.0-flash")

PARSING KEYWORDS:
- "using [name]" or "with [name]" → Agent or credential name
- "model [name]" → Specific model to use
- If not mentioned → Leave as null

CONFIGURATION STEPS:

1. IF agent name mentioned in command:
   - Call get_agents(search="")
   - Find agent where name contains mentioned keywords (case-insensitive substring match)
   - If found: Extract agent_id and agent_name
   - If no match: Set agent_id=null, include warning in message

2. IF credential name mentioned in command:
   - Call get_credentials(search="", category="LLM")
   - Find credential where name contains mentioned keywords (case-insensitive substring match)
   - If found: Extract llm_credential_id and credential_name
   - If no match: Set llm_credential_id=null, include warning in message

3. SET model field:
   - If user specified "model X" → Use X
   - If credential contains "gemini" → Default to "gemini-2.0-flash"
   - Otherwise → null (will use credential's default)

4. ALWAYS SET these defaults:
   - batch_size: 100
   - timeout: 30

5. NEVER auto-create input_mapping:
   - Always leave input_mapping empty or omit it
   - User will configure this manually in the UI

6. FORMAT message with what was configured:
   - Start with "✅ Added agent node"
   - If agent set: "with [Agent Name] (ID: X)"
   - If credential set: "and [Credential Name] (ID: Y)"
   - If model set: "using model [model]"
   - Add warnings for missing required fields: "⚠️ Agent not configured" or "⚠️ LLM credential not configured"

EXAMPLES (Complete NodeAddAction Structures):

Example 1: "add agent node"
Action: Create node with all null values (except defaults)
Output: NodeAddAction(
    node_id="agent-1",
    node=NodeConfig(
        node_type="agent",
        position=NodePosition(x=100, y=200),
        config={"agent_id": None, "llm_credential_id": None, "batch_size": 100, "timeout": 30},
        label="AI Agent"
    ),
    message="✅ Added agent node. Configure agent and LLM credential in node settings."
)

Example 2: "add agent node using data analyst agent"
Action: Call get_agents() → Find "Data analyst agent" (ID: 9)
Output: NodeAddAction(
    node_id="agent-1",
    node=NodeConfig(
        node_type="agent",
        position=NodePosition(x=100, y=200),
        config={"agent_id": 9, "llm_credential_id": None, "batch_size": 100, "timeout": 30},
        label="AI Agent"
    ),
    message="✅ Added agent node with Data analyst agent (ID: 9). ⚠️ LLM credential not configured - configure in node settings."
)

Example 3: "add agent node with gemini credential"
Action: Call get_credentials(category="LLM") → Find credential with "gemini" (ID: 3)
Output: NodeAddAction(
    node_id="agent-1",
    node=NodeConfig(
        node_type="agent",
        position=NodePosition(x=100, y=200),
        config={"agent_id": None, "llm_credential_id": 3, "model": "gemini-2.0-flash", "batch_size": 100, "timeout": 30},
        label="AI Agent"
    ),
    message="✅ Added agent node with Gemini credential (ID: 3), model: gemini-2.0-flash. ⚠️ Agent not configured - configure in node settings."
)

Example 4: "add agent node using text classifier with openai credential"
Action: Call get_agents() → Find "Text Classifier" (ID: 6), Call get_credentials() → Find "openai" (ID: 5)
Output: NodeAddAction(
    node_id="agent-1",
    node=NodeConfig(
        node_type="agent",
        position=NodePosition(x=100, y=200),
        config={"agent_id": 6, "llm_credential_id": 5, "batch_size": 100, "timeout": 30},
        label="AI Agent"
    ),
    message="✅ Added agent node with Text Classifier (ID: 6) and OpenAI credential (ID: 5)."
)

Example 5: "add agent node using sentiment analyzer with gemini credential model gemini-2.0-flash"
Action: Call get_agents() → Find "Call Transcript Sentiment Analyzer" (ID: 3), Call get_credentials() → Find "gemini" (ID: 3)
Output: NodeAddAction(
    node_id="agent-1",
    node=NodeConfig(
        node_type="agent",
        position=NodePosition(x=100, y=200),
        config={"agent_id": 3, "llm_credential_id": 3, "model": "gemini-2.0-flash", "batch_size": 100, "timeout": 30},
        label="AI Agent"
    ),
    message="✅ Added agent node with Call Transcript Sentiment Analyzer (ID: 3), Gemini credential (ID: 3), model: gemini-2.0-flash."
)

CRITICAL RULES:
- ONLY set values explicitly mentioned by user
- Use tools to FIND IDs via name matching, never guess IDs
- NEVER auto-select if user didn't specify
- NEVER create input_mapping automatically
- If name matching fails, set to null and warn user in message
- Always provide clear feedback about what was configured vs what needs manual setup

NODE UPDATE/CONFIGURATION:

When user says "configure", "update", or "set" for an EXISTING node:
1. Check workflow state to find the existing node by type
2. Use tools to find resource IDs if names are mentioned
3. Parse JSON from tool results to extract numeric IDs
4. Return TYPE-SPECIFIC update action based on node type

IMPORTANT: Tools return JSON arrays. Parse them to extract IDs!
- get_agents() returns: [{"id": 9, "name": "Data analyst agent", ...}]
- get_credentials() returns: [{"id": 3, "name": "Gemini", ...}]
- Extract the "id" field from matching JSON object and use in the action

AGENT NODE UPDATE EXAMPLES:

Example 1: "configure agent node with data analyst agent"
Workflow state: node "agent-1" (type: agent) exists
Steps:
  1. Call get_agents()
  2. Tool returns JSON: [{"id": 9, "name": "Data analyst agent", ...}, ...]
  3. Find object where name contains "data analyst" → Extract id: 9
  4. Return AgentNodeUpdateAction with agent_id field
Output: AgentNodeUpdateAction(
    node_id="agent-1",
    agent_id=9,
    llm_credential_id=None,
    model=None,
    message="✅ Configured agent-1 with Data analyst agent (ID: 9)"
)

Example 2: "update agent with gemini credential"
Workflow state: node "agent-1" (type: agent) exists
Steps:
  1. Call get_credentials(category="LLM")
  2. Tool returns JSON: [{"id": 3, "name": "Gemini", ...}, ...]
  3. Find object where name contains "gemini" → Extract id: 3
  4. Set model to "gemini-2.0-flash" (default for gemini)
Output: AgentNodeUpdateAction(
    node_id="agent-1",
    agent_id=None,
    llm_credential_id=3,
    model="gemini-2.0-flash",
    message="✅ Updated agent-1 with Gemini credential (ID: 3), model: gemini-2.0-flash"
)

Example 3: "set agent model to gemini-2.0-flash"
Workflow state: node "agent-1" (type: agent) exists
Output: AgentNodeUpdateAction(
    node_id="agent-1",
    agent_id=None,
    llm_credential_id=None,
    model="gemini-2.0-flash",
    message="✅ Set agent-1 model to gemini-2.0-flash"
)

DATABASE NODE UPDATE EXAMPLE:

Example 4: "configure database node with postgres credential"
Workflow state: node "database-1" (type: database) exists
Steps:
  1. Call get_credentials(category="RDBMS")
  2. Tool returns JSON: [{"id": 2, "name": "PostgreSQL prod", ...}, ...]
  3. Find object where name contains "postgres" → Extract id: 2
Output: DatabaseNodeUpdateAction(
    node_id="database-1",
    credential_id=2,
    query=None,
    message="✅ Configured database-1 with PostgreSQL credential (ID: 2)"
)

CRITICAL NODE UPDATE RULES:
- Use EXISTING node_id from workflow state (e.g., "agent-1", "database-1")
- Use TYPE-SPECIFIC action: AgentNodeUpdateAction for agents, DatabaseNodeUpdateAction for databases
- Set fields explicitly (agent_id=9) not in a dict
- "configure/update" = Type-specific update action for existing nodes
- "add/create" = NodeAddAction for new nodes
- Always check workflow state first to verify node exists

DETAILED AGENT QUERIES:
When user asks about a specific agent's abilities, capabilities, or what it does:
1. Call get_agents() if needed to find the agent
2. Parse JSON to extract agent_id
3. Call get_agent_details(agent_id) to fetch complete information
4. Return ConversationalResponse with formatted details about prompts, tools, and capabilities

Examples:
  User: "what agents are available?"
  You: [Call get_agents()] → Parse JSON → Format as friendly list in ConversationalResponse

  User: "what are the abilities of data analyst agent?"
  You: [Call get_agents()] → Parse JSON, find {"id": 9, "name": "Data analyst agent"} → [Call get_agent_details(9)] → Return detailed capabilities in ConversationalResponse

  User: "what does the text classifier do?"
  You: [Call get_agents()] → Parse JSON to find id → [Call get_agent_details(id)] → Return detailed info

TOOL LISTING QUERIES:
When user asks about available tools:
1. Call get_internal_tools(search="") to get built-in tools (SerpAPI, database tools, etc.)
2. Call get_mcp_servers(search="") to get external MCP servers and their tools
3. Parse both JSON responses
4. Return ConversationalResponse with categorized, friendly list of tools

Examples:
  User: "what tools do we have?"
  You: [Call get_internal_tools() AND get_mcp_servers()] → Parse both JSON responses → Return formatted list like:
    "📦 Internal Tools (3):
     - SerpAPI (Web search tool, requires API credential)
     - Database Query (Execute SQL queries)
     - Text Analysis (NLP processing)

     🌐 MCP Servers (2):
     - GitHub Server (15 tools for repo management)
     - Slack Server (8 tools for messaging)"

  User: "what internal tools are there?"
  You: [Call get_internal_tools()] → Parse JSON → Return friendly list of internal tools only

  User: "show me MCP servers"
  You: [Call get_mcp_servers()] → Parse JSON → Return friendly list of MCP servers

TOOLBOX NODE UPDATE EXAMPLES:

When user says "configure toolbox with [tool name] using [credential name]":
1. Call get_internal_tools(search="tool name") to find the tool
2. Parse JSON response to extract tool_id
3. Call get_credentials(search="credential name") to find the credential
4. Parse JSON response to extract credential_id
5. Return ToolboxNodeUpdateAction with internal_tool_attachments

Example 5: "configure toolbox with Database Toolset using call transcripts db credential"
Workflow state: node "toolbox-1" (type: toolbox) exists
Steps:
  1. Call get_internal_tools(search="Database Toolset")
  2. Tool returns JSON: [{"id": 3, "name": "Database Toolset", "requires_credential": true, "required_credential_type": "PostgreSQL"}]
  3. Extract tool_id: 3
  4. Call get_credentials(search="call transcripts", category="RDBMS")
  5. Credential returns JSON: [{"id": 7, "name": "Call Transcripts DB", "credential_type_name": "PostgreSQL"}]
  6. Extract credential_id: 7
  7. Return ToolboxNodeUpdateAction
Output: ToolboxNodeUpdateAction(
    node_id="toolbox-1",
    mcp_server_ids=None,
    internal_tool_attachments=[InternalToolAttachment(tool_id=3, credential_id=7)],
    message="✅ Configured toolbox-1 with Database Toolset using Call Transcripts DB credential"
)

Example 6: "add GitHub MCP server to toolbox"
Workflow state: node "toolbox-1" (type: toolbox) exists
Steps:
  1. Call get_mcp_servers(search="GitHub")
  2. Server returns JSON: [{"id": 2, "name": "GitHub Server", "tools_count": 15}]
  3. Extract server_id: 2
  4. Return ToolboxNodeUpdateAction
Output: ToolboxNodeUpdateAction(
    node_id="toolbox-1",
    mcp_server_ids=[2],
    internal_tool_attachments=None,
    message="✅ Added GitHub Server (15 tools) to toolbox-1"
)

Example 7: "configure toolbox with SerpAPI tool using my api key"
Workflow state: node "toolbox-1" (type: toolbox) exists
Steps:
  1. Call get_internal_tools(search="SerpAPI")
  2. Extract tool_id
  3. Call get_credentials(search="api key", category="API")
  4. Extract credential_id
  5. Return ToolboxNodeUpdateAction with internal_tool_attachments
Output: ToolboxNodeUpdateAction(
    node_id="toolbox-1",
    mcp_server_ids=None,
    internal_tool_attachments=[InternalToolAttachment(tool_id=1, credential_id=4)],
    message="✅ Configured toolbox-1 with SerpAPI using API Key credential"
)

IMPORTANT FOR TOOLBOX CONFIGURATION:
- Internal tools ALWAYS need credentials (internal_tool_attachments format)
- MCP servers don't need credentials (mcp_server_ids format)
- Both can be set in same ToolboxNodeUpdateAction
- Parse JSON responses carefully to extract numeric IDs
- Verify tool's required_credential_type matches credential's credential_type_name

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
    output_type=ConversationalResponse | NodeAddAction | AgentNodeUpdateAction | DatabaseNodeUpdateAction | ToolboxNodeUpdateAction | EdgeAddAction | NodeRemoveAction | EdgeRemoveAction,
    instructions=AGENT_PROMPT,
)

print(f"\n{'*'*80}")
print(f"🤖 WORKFLOW BUILDER AGENT INITIALIZED")
print(f"   Model: {MODEL_NAME}")
print(f"   Output: ConversationalResponse | NodeAddAction | AgentNodeUpdateAction | DatabaseNodeUpdateAction | ToolboxNodeUpdateAction | EdgeAddAction | NodeRemoveAction | EdgeRemoveAction")
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
        category: Credential category (default: RDBMS, use "LLM" for AI credentials)

    Returns:
        JSON array string: [{"id": int, "name": str, "credential_type_name": str, "description": str}, ...]
        Parse this JSON to extract credential IDs for use in config_updates.
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
                # Return JSON array of credential objects with context
                creds_data = [
                    {
                        "id": c.id,
                        "name": c.name,
                        "credential_type_name": c.credential_type_name,
                        "description": c.description or ""
                    }
                    for c in credentials
                ]

                result = f"Found {len(credentials)} credentials:\n{json.dumps(creds_data, indent=2)}"

                print(f"✅ get_credentials SUCCESS: {len(credentials)} credentials found")
                return result
            else:
                print(f"✅ get_credentials SUCCESS: 0 credentials found")
                return "No credentials found: []"

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"❌ get_credentials ERROR: {error_msg}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error fetching credentials: {e.response.status_code}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = str(e)
        print(f"❌ get_credentials EXCEPTION: {error_msg}")
        return json.dumps({"error": error_msg})


@chat_agent.tool
async def get_agents(ctx: RunContext[str], search: str = "") -> str:
    """
    Get available AI agents for the current project.

    Args:
        search: Optional search term (usually empty to get all)

    Returns:
        JSON array string: [{"id": int, "name": str, "description": str, "return_type": str}, ...]
        Parse this JSON to extract agent IDs for use in config_updates.
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
                # Return JSON array of agent objects with context
                agents_data = [
                    {
                        "id": a.id,
                        "name": a.name,
                        "description": a.description or "",
                        "return_type": a.return_type or ""
                    }
                    for a in agents
                ]

                result = f"Found {len(agents)} agents:\n{json.dumps(agents_data, indent=2)}"

                print(f"✅ get_agents SUCCESS: {len(agents)} agents found")
                return result
            else:
                print(f"✅ get_agents SUCCESS: 0 agents found")
                return "No agents found: []"

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"❌ get_agents ERROR: {error_msg}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error fetching agents: {e.response.status_code}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = str(e)
        print(f"❌ get_agents EXCEPTION: {error_msg}")
        return json.dumps({"error": error_msg})


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
async def get_internal_tools(ctx: RunContext[str], search: str = "", category: str = "") -> str:
    """
    Get available internal tools (built-in tools like SerpAPI, database tools, etc.).

    Use this when user asks "what tools?", "what internal tools?", or "what tools do we have?".

    Args:
        search: Optional search term to filter tools by name/description
        category: Optional category filter (e.g., 'WEB', 'DATABASE', 'API')

    Returns:
        JSON string with list of internal tools
    """
    session_id = ctx.deps

    print(f"\n{'='*80}")
    print(f"🔧 TOOL: get_internal_tools")
    print(f"   Session ID: {session_id}")
    print(f"   Search: {search!r}")
    print(f"   Category: {category!r}")
    print(f"{'='*80}\n")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{DJANGO_API_BASE}/api/builder-tools/get_internal_tools/"
            params = {"session_id": session_id, "search": search}
            if category:
                params["category"] = category

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            print(f"✅ get_internal_tools SUCCESS: {len(data)} internal tools found")

            if data:
                # Return JSON array with context
                tools_data = [
                    {
                        "id": t.get("id"),
                        "name": t.get("name"),
                        "description": t.get("description", ""),
                        "category": t.get("category", ""),
                        "tool_type": t.get("tool_type", ""),
                        "requires_credential": t.get("requires_credential", False),
                        "required_credential_type": t.get("required_credential_type_name", "")
                    }
                    for t in data
                ]
                result = f"Found {len(tools_data)} internal tools:\n{json.dumps(tools_data, indent=2)}"
                return result
            else:
                return "No internal tools found."

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"❌ get_internal_tools HTTP ERROR: {error_msg}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error fetching internal tools: {e.response.status_code}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = str(e)
        print(f"❌ get_internal_tools EXCEPTION: {error_msg}")
        return json.dumps({"error": error_msg})


@chat_agent.tool
async def get_mcp_servers(ctx: RunContext[str], search: str = "") -> str:
    """
    Get available MCP (Model Context Protocol) servers and their tools.

    Use this when user asks "what MCP servers?", "what external tools?", or "what tools do we have?".

    Args:
        search: Optional search term to filter servers by name/description

    Returns:
        JSON string with list of MCP servers and their tool counts
    """
    session_id = ctx.deps

    print(f"\n{'='*80}")
    print(f"🔧 TOOL: get_mcp_servers")
    print(f"   Session ID: {session_id}")
    print(f"   Search: {search!r}")
    print(f"{'='*80}\n")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{DJANGO_API_BASE}/api/builder-tools/get_mcp_servers/"
            params = {"session_id": session_id, "search": search}

            response = await client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            print(f"✅ get_mcp_servers SUCCESS: {len(data)} MCP servers found")

            if data:
                # Return JSON array with context
                servers_data = [
                    {
                        "id": s.get("id"),
                        "name": s.get("name"),
                        "description": s.get("description", ""),
                        "url": s.get("url", ""),
                        "tools_count": s.get("tools_count", 0),
                        "is_healthy": s.get("is_healthy", False)
                    }
                    for s in data
                ]
                result = f"Found {len(servers_data)} MCP servers:\n{json.dumps(servers_data, indent=2)}"
                return result
            else:
                return "No MCP servers found."

    except httpx.HTTPStatusError as e:
        error_msg = f"HTTP {e.response.status_code}: {e.response.text}"
        print(f"❌ get_mcp_servers HTTP ERROR: {error_msg}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error fetching MCP servers: {e.response.status_code}")
        return json.dumps({"error": error_msg})
    except Exception as e:
        error_msg = str(e)
        print(f"❌ get_mcp_servers EXCEPTION: {error_msg}")
        return json.dumps({"error": error_msg})


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
        edges = current_workflow.get("edges", [])
        print(f"   Current workflow: {len(nodes)} nodes, {len(edges)} edges")

        workflow_context = f"\n\nCURRENT WORKFLOW STATE:\n"
        workflow_context += f"Total nodes: {len(nodes)}\n"
        workflow_context += "Existing nodes:\n"
        for node in nodes:
            workflow_context += f"  - {node.get('id')} ({node.get('type')}) at x={node.get('position', {}).get('x', 0)}\n"

        # Add edges information
        if edges:
            workflow_context += f"\nTotal edges: {len(edges)}\n"
            workflow_context += "Existing edges:\n"
            for edge in edges:
                source = edge.get('source', 'unknown')
                target = edge.get('target', 'unknown')
                edge_id = edge.get('id', 'unknown')
                target_handle = edge.get('targetHandle')
                source_handle = edge.get('sourceHandle')

                edge_desc = f"  - {source} → {target}"
                if target_handle:
                    edge_desc += f" (target: {target_handle})"
                if source_handle:
                    edge_desc += f" (source: {source_handle})"
                edge_desc += f" [ID: {edge_id}]\n"
                workflow_context += edge_desc
        else:
            workflow_context += "\nNo edges yet\n"

        workflow_context += f"\nNext node should be positioned at x={100 + (len(nodes) * 300)}, y=200\n"
    else:
        print(f"   Current workflow: empty (starting fresh)")
        workflow_context = "\n\nCURRENT WORKFLOW STATE: Empty (no nodes yet)\nNext node should be positioned at x=100, y=200\n"

    # Augment user prompt with workflow context
    augmented_prompt = f"{workflow_context}\nUSER REQUEST: {prompt}"

    async def stream():
        try:
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
            print(f"   🤖 Calling chat_agent.run()...")

            try:
                # Add 60 second timeout
                result = await asyncio.wait_for(
                    chat_agent.run(augmented_prompt, message_history=messages, deps=session_id),
                    timeout=60.0
                )
                output = result.output
                print(f"   ✅ Agent completed successfully, output type: {type(output).__name__}")

            except asyncio.TimeoutError:
                error_msg = "Agent execution timed out after 60 seconds"
                print(f"   ❌ TIMEOUT: {error_msg}")
                yield json.dumps({
                    "role": "assistant",
                    "timestamp": now_iso(),
                    "content": f"⚠️ Error: {error_msg}. The agent took too long to respond."
                }).encode("utf-8") + b"\n"
                return

            except Exception as agent_error:
                error_msg = f"Agent execution failed: {str(agent_error)}"
                print(f"   ❌ AGENT ERROR: {error_msg}")
                print(f"   Traceback:")
                traceback.print_exc()
                yield json.dumps({
                    "role": "assistant",
                    "timestamp": now_iso(),
                    "content": f"⚠️ Error: {error_msg}"
                }).encode("utf-8") + b"\n"
                return

            # Determine output type and stream appropriate response
            print(f"   📊 Processing output type...")
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

            elif isinstance(output, AgentNodeUpdateAction):
                # Agent node update action
                print(f"   ✏️ Intent: AGENT_NODE_UPDATE ({output.node_id})")
                # Build config_updates from non-None fields
                config_updates = {}
                if output.agent_id is not None:
                    config_updates["agent_id"] = output.agent_id
                if output.llm_credential_id is not None:
                    config_updates["llm_credential_id"] = output.llm_credential_id
                if output.model is not None:
                    config_updates["model"] = output.model
                print(f"      Config updates: {config_updates}")

                yield json.dumps({
                    "role": "assistant",
                    "timestamp": now_iso(),
                    "content": output.message,
                    "action": "node_update",
                    "data": {
                        "node_id": output.node_id,
                        "config_updates": config_updates
                    }
                }).encode("utf-8") + b"\n"

            elif isinstance(output, DatabaseNodeUpdateAction):
                # Database node update action
                print(f"   ✏️ Intent: DATABASE_NODE_UPDATE ({output.node_id})")
                # Build config_updates from non-None fields
                config_updates = {}
                if output.credential_id is not None:
                    config_updates["credential_id"] = output.credential_id
                if output.query is not None:
                    config_updates["query"] = output.query
                print(f"      Config updates: {config_updates}")

                yield json.dumps({
                    "role": "assistant",
                    "timestamp": now_iso(),
                    "content": output.message,
                    "action": "node_update",
                    "data": {
                        "node_id": output.node_id,
                        "config_updates": config_updates
                    }
                }).encode("utf-8") + b"\n"

            elif isinstance(output, ToolboxNodeUpdateAction):
                # Toolbox node update action
                print(f"   ✏️ Intent: TOOLBOX_NODE_UPDATE ({output.node_id})")
                # Build config_updates from non-None fields
                config_updates = {}
                if output.mcp_server_ids is not None:
                    config_updates["mcp_server_ids"] = output.mcp_server_ids
                if output.internal_tool_attachments is not None:
                    # Convert InternalToolAttachment objects to dict format for frontend
                    config_updates["internal_tool_attachments"] = [
                        {"tool_id": att.tool_id, "credential_id": att.credential_id}
                        for att in output.internal_tool_attachments
                    ]
                print(f"      Config updates: {config_updates}")

                yield json.dumps({
                    "role": "assistant",
                    "timestamp": now_iso(),
                    "content": output.message,
                    "action": "node_update",
                    "data": {
                        "node_id": output.node_id,
                        "config_updates": config_updates
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
                print(f"   ✂️ Intent: EDGE_REMOVE ({output.source_node_id} → {output.target_node_id})")
                print(f"      Looking for edge with:")
                print(f"        source_handle: {repr(output.source_handle)}")
                print(f"        target_handle: {repr(output.target_handle)}")

                # Find the actual edge in current workflow state
                edge_id = None
                if current_workflow and current_workflow.get("edges"):
                    edges = current_workflow["edges"]
                    print(f"      Searching through {len(edges)} edges...")
                    for edge in edges:
                        print(f"      Checking edge: {edge.get('source')} → {edge.get('target')}")
                        print(f"        edge.sourceHandle: {repr(edge.get('sourceHandle'))}")
                        print(f"        edge.targetHandle: {repr(edge.get('targetHandle'))}")

                        # Match by source, target, and handles
                        source_match = edge.get("source") == output.source_node_id
                        target_match = edge.get("target") == output.target_node_id
                        source_handle_match = edge.get("sourceHandle") == output.source_handle
                        target_handle_match = edge.get("targetHandle") == output.target_handle

                        print(f"        Matches: source={source_match}, target={target_match}, source_handle={source_handle_match}, target_handle={target_handle_match}")

                        if source_match and target_match and source_handle_match and target_handle_match:
                            edge_id = edge.get("id")
                            print(f"      ✅ Found edge to remove: {edge_id}")
                            break

                if edge_id:
                    yield json.dumps({
                        "role": "assistant",
                        "timestamp": now_iso(),
                        "content": output.message,
                        "action": "edge_remove",
                        "data": {
                            "edge_id": edge_id
                        }
                    }).encode("utf-8") + b"\n"
                else:
                    # Edge not found - send error message
                    error_msg = f"⚠️ Could not find edge between {output.source_node_id} and {output.target_node_id}"
                    print(f"      WARNING: {error_msg}")
                    yield json.dumps({
                        "role": "assistant",
                        "timestamp": now_iso(),
                        "content": error_msg
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

        except Exception as stream_error:
            error_msg = f"Streaming error: {str(stream_error)}"
            print(f"   ❌ STREAM ERROR: {error_msg}")
            traceback.print_exc()
            yield json.dumps({
                "role": "assistant",
                "timestamp": now_iso(),
                "content": f"⚠️ Unexpected error: {error_msg}"
            }).encode("utf-8") + b"\n"

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
