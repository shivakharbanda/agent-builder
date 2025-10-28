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

from pydantic_ai import Agent
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
from models import ConversationalResponse, NodeAddAction, EdgeAddAction, NodeRemoveAction, EdgeRemoveAction, NodeConfig, NodePosition


# Load environment variables
load_dotenv()


# ============================================================================
# Configuration
# ============================================================================

DB_PATH = os.getenv("DB_PATH", "messages.db")
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash-latest")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

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

You can handle TWO types of interactions:

1. **CONVERSATIONAL**: When user is chatting, asking questions, greeting, or seeking help
   - Return ConversationalResponse with a friendly message
   - Be helpful, concise, and guide them

2. **NODE ADD REQUEST**: When user explicitly asks to add a workflow node
   - Detect the node type they want
   - Generate appropriate configuration
   - Return NodeAddAction with the node details

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
- **Node creation**: if user says "add", "need", "create" + node name = NodeAddAction
- **Edge creation**: if user says "connect", "join", "link" + node IDs = EdgeAddAction
- **Node removal**: if user says "remove", "delete" + node type = NodeRemoveAction
- **Edge removal**: if user says "disconnect", "remove edge", "delete connection" = EdgeRemoveAction
- **Conversation**: Otherwise = ConversationalResponse
- Keep messages friendly and concise
- Provide helpful guidance
- Always check workflow state before operations to verify nodes/edges exist
- ALWAYS use exact IDs from workflow state, never invent IDs
"""

# Create agent with structured output
chat_agent = Agent(
    model,
    output_type=ConversationalResponse | NodeAddAction | EdgeAddAction | NodeRemoveAction | EdgeRemoveAction,
    instructions=AGENT_PROMPT,
)

print(f"\n{'*'*80}")
print(f"🤖 WORKFLOW BUILDER AGENT INITIALIZED")
print(f"   Model: {MODEL_NAME}")
print(f"   Output: ConversationalResponse | NodeAddAction | EdgeAddAction | NodeRemoveAction | EdgeRemoveAction")
print(f"   Mode: Intent-based routing (conversation + node/edge add/remove)")
print(f"{'*'*80}\n")


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
        result = await chat_agent.run(augmented_prompt, message_history=messages)
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
