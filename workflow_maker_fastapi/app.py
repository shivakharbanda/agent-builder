from __future__ import annotations

import os
import re
import json
import asyncio
import uuid
from typing import Any, Literal, List, Dict
from datetime import datetime, timezone

import fastapi
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response, StreamingResponse
from pydantic import BaseModel

import aiosqlite
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from pydantic_ai import Agent, UnexpectedModelBehavior
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


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

DB_PATH = os.getenv("DB_PATH", "messages.db")

# Model configuration
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash-latest")

# Use Google API key for Generative Language API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set. Please set your Google API key in the .env file.")

provider = GoogleProvider(api_key=GOOGLE_API_KEY)

model = GoogleModel(MODEL_NAME, provider=provider)


# ------------------------------------------------------------------------------
# Generator agent prompt: workflow structure generation
# ------------------------------------------------------------------------------

GENERATOR_PROMPT = """
You are an expert workflow builder that creates data processing workflows through focused conversation.

GOAL: Ask targeted questions to understand the user's workflow needs, present a preview, get confirmation, then output workflow configuration JSON.

CONVERSATION FLOW:
1) User describes their workflow goal (e.g., "intent analysis", "data processing pipeline")
2) Ask clarifying questions ONLY about unclear or missing details:
   - Data source: Where does data come from? (database table, API, file)
   - Processing: What operations/agents process the data? What filters or transformations?
   - Data destination: Where do results go? (database, file, API)
   - Additional logic: Any conditionals, branching, or custom scripts needed?
3) When you have enough info, present a clear preview of the workflow structure
4) After user confirms (yes/okay/looks good/proceed/etc), output ONLY the raw JSON config

WORKFLOW PATTERNS:
- Simple linear: Database → Agent → Output
- Filtered flow: Database → Filter → Agent → Output
- Branching: Database → Agent → Conditional → [Output A, Output B]
- Multi-step: Database → Agent 1 → Script → Agent 2 → Output

NODE TYPES AVAILABLE:
- database: Read from database tables (source node)
- agent: AI/ML processing with configured agents (processor)
- filter: Filter data based on conditions (processor)
- script: Custom Python/JavaScript code execution (processor)
- conditional: Branch execution based on conditions (control flow)
- output: Save to database/file/API (sink node)

QUESTION STRATEGY:
- Ask 1-3 focused questions maximum
- Be direct and specific
- Make reasonable assumptions when possible
- Don't ask about obvious things
- If user provides all info upfront, skip to preview

WHEN TO PRESENT PREVIEW:
Present preview when you understand:
- The core use case/purpose
- Data source (where data comes from)
- Processing steps (what happens to the data)
- Destination (where results go)

PREVIEW FORMAT:
Present the configuration clearly:
---
Perfect! I'll create a workflow with this structure:

**Workflow:** [Name]
**Description:** [What it does]

**Flow:**
1. Database Input → reads from [table_name]
2. [Processing Node] → [what it does]
3. Output → saves to [destination]

**Connections:** Node 1 → Node 2 → Node 3

Should I generate this configuration?
---

CONFIRMATION DETECTION:
If user responds affirmatively (yes, okay, ok, sure, looks good, perfect, go ahead, proceed, correct, that's right, etc.),
IMMEDIATELY output ONLY the raw JSON with NO additional text, NO code fences, NO markdown.

FINAL OUTPUT (only after user confirmation):
Output ONLY the JSON object (no markdown, no code fences, no extra text):
{
  "name": "Workflow Name",
  "description": "What this workflow does",
  "nodes": [
    {
      "id": "node_1",
      "type": "database|agent|filter|script|conditional|output",
      "position": {"x": number, "y": number},
      "config": {
        "label": "Node Display Name"
      }
    }
  ],
  "edges": [
    {"id": "edge_1", "source": "node_1", "target": "node_2"}
  ],
  "properties": {
    "timeout": 3600,
    "retry_count": 3
  }
}

POSITION GUIDELINES:
- Arrange nodes left-to-right with ~300px spacing
- Linear flows: x = 100, 400, 700, 1000, etc. | y = 200 (centered)
- Branching flows:
  * Main path: y = 200
  * Top branch: y = 100
  * Bottom branch: y = 300
- Start at x=100 for first node

NODE CONFIG GUIDELINES:
- Keep configs MINIMAL - only label is required
- User will configure details (credentials, queries, schemas) in UI later
- Focus on workflow STRUCTURE, not detailed configuration
- Example configs:
  * database: {"label": "Customer Data"}
  * agent: {"label": "Intent Classifier"}
  * filter: {"label": "Active Users Only"}
  * output: {"label": "Save Results"}

IMPORTANT:
- NEVER include code fences (```) around JSON output
- NEVER add explanatory text after JSON output
- Output must be valid, parseable JSON
- All node IDs must be unique (node_1, node_2, etc.)
- All edge IDs must be unique (edge_1, edge_2, etc.)
- Every edge source/target must reference existing node IDs
"""

generator_agent = Agent(model, system_prompt=GENERATOR_PROMPT)


# ------------------------------------------------------------------------------
# FastAPI app + CORS
# ------------------------------------------------------------------------------

app = fastapi.FastAPI(title="Workflow-Builder Generator (Gemini)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],   # tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ------------------------------------------------------------------------------
# SQLite persistence (compatible with PydanticAI chat example)
# ------------------------------------------------------------------------------

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


@app.on_event("startup")
async def on_startup() -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(CREATE_TABLE_SQL)
        await db.execute(CREATE_INDEX_SQL)
        await db.commit()


async def add_messages_blob(session_id: str, blob: bytes) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(INSERT_SQL, (datetime.now(timezone.utc).isoformat(), session_id, blob))
        await db.commit()


async def load_messages(session_id: str) -> List[ModelMessage]:
    async with aiosqlite.connect(DB_PATH) as db:
        cur = await db.execute(SELECT_BY_SESSION_SQL, (session_id,))
        rows = await cur.fetchall()
    messages: List[ModelMessage] = []
    for (blob,) in rows:
        messages.extend(ModelMessagesTypeAdapter.validate_json(blob))
    return messages


async def reset_messages(session_id: str) -> None:
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(DELETE_BY_SESSION_SQL, (session_id,))
        await db.commit()


# ------------------------------------------------------------------------------
# Utilities
# ------------------------------------------------------------------------------

def now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def to_chat_message(m: ModelMessage) -> Dict[str, str]:
    first = m.parts[0]
    if isinstance(m, ModelRequest) and isinstance(first, UserPromptPart):
        return {"role": "user", "timestamp": first.timestamp.isoformat(), "content": first.content}
    if isinstance(m, ModelResponse) and isinstance(first, TextPart):
        return {"role": "model", "timestamp": m.timestamp.isoformat(), "content": first.content}
    raise UnexpectedModelBehavior("Unexpected message type for chat app")


def extract_and_validate_workflow(text: str) -> dict | None:
    """
    Extract and validate workflow configuration JSON from text.
    Handles both raw JSON and markdown code fence wrapped JSON.
    Returns parsed dict if valid workflow config, None otherwise.
    """
    if not text:
        return None

    candidate = text.strip()

    # Handle markdown code fences
    if candidate.startswith('```'):
        lines = candidate.split('\n')
        if len(lines) >= 3:  # Need at least opening fence, content, closing fence
            # Remove first line (```json or ```) and last line (```)
            candidate = '\n'.join(lines[1:-1]).strip()

    # Try to parse as JSON
    try:
        payload = json.loads(candidate)

        # Validate it's a workflow config with required fields
        if not isinstance(payload, dict):
            return None

        # Check required fields
        if not (isinstance(payload.get("name"), str) and payload["name"].strip()):
            return None
        if not (isinstance(payload.get("description"), str) and payload["description"].strip()):
            return None
        if not (isinstance(payload.get("nodes"), list) and len(payload["nodes"]) > 0):
            return None

        # Validate nodes structure
        valid_node_types = {"database", "agent", "filter", "script", "conditional", "output"}
        node_ids = set()

        for node in payload["nodes"]:
            if not isinstance(node, dict):
                return None
            if not all(k in node for k in ["id", "type", "position"]):
                return None
            if node["type"] not in valid_node_types:
                return None
            if not isinstance(node.get("position"), dict):
                return None
            if not ("x" in node["position"] and "y" in node["position"]):
                return None
            node_ids.add(node["id"])

        # Validate edges
        if not isinstance(payload.get("edges"), list):
            return None

        for edge in payload["edges"]:
            if not isinstance(edge, dict):
                return None
            if not all(k in edge for k in ["id", "source", "target"]):
                return None
            # Validate edge references valid nodes
            if edge["source"] not in node_ids or edge["target"] not in node_ids:
                return None

        # Properties are optional but should be dict if present
        if "properties" in payload and not isinstance(payload["properties"], dict):
            return None

        return payload

    except (json.JSONDecodeError, KeyError, TypeError):
        return None


# ------------------------------------------------------------------------------
# API models
# ------------------------------------------------------------------------------

class GenerateRequest(BaseModel):
    prompt: str
    session_id: str


class SessionScopedRequest(BaseModel):
    session_id: str


class NewSessionResponse(BaseModel):
    session_id: str


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@app.get("/healthz")
async def healthz() -> Response:
    return Response("ok", media_type="text/plain")


@app.post("/session/", response_model=NewSessionResponse)
async def new_session() -> NewSessionResponse:
    """Create a new session and return its ID."""
    return NewSessionResponse(session_id=str(uuid.uuid4()))


@app.post("/generate/")
async def generate_workflow(body: GenerateRequest) -> StreamingResponse:
    """
    Conversational workflow generation: ask focused questions, then output final config JSON.
    Uses session-based conversation with generator agent.
    """
    prompt = body.prompt
    session_id = body.session_id

    async def stream():
        # Immediately echo the user message so the client can render it.
        yield json.dumps({"role": "user", "timestamp": now_iso(), "content": prompt}).encode("utf-8") + b"\n"

        messages = await load_messages(session_id)

        # Run the generator agent with full history and stream model output.
        async with generator_agent.run_stream(prompt, message_history=messages) as result:
            async for text in result.stream_output(debounce_by=0.01):
                m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp())
                yield json.dumps(to_chat_message(m)).encode("utf-8") + b"\n"

        # Persist new messages (both the user request and the model response).
        await add_messages_blob(session_id, result.new_messages_json())

    return StreamingResponse(stream(), media_type="text/plain")


@app.get("/generate/finalize/")
async def generate_finalize(session_id: str) -> Response:
    """
    Attempts to parse the last assistant message from generator conversation as the final JSON config.
    Returns 202 if not finalized yet, 200 with JSON if valid config found.
    """
    messages = await load_messages(session_id)
    if not messages:
        return Response("Not finalized yet.", media_type="text/plain", status_code=202)

    # Find last assistant message and try to extract valid JSON
    for m in reversed(messages):
        if isinstance(m, ModelResponse) and isinstance(m.parts[0], TextPart):
            candidate = m.parts[0].content
            payload = extract_and_validate_workflow(candidate)

            if payload:
                # Valid workflow config found
                return Response(json.dumps(payload, indent=2), media_type="application/json")

    # No valid config found in any message
    return Response("Not finalized yet.", media_type="text/plain", status_code=202)


@app.post("/reset/")
async def reset(body: SessionScopedRequest) -> Response:
    """Reset conversation for a session."""
    await reset_messages(body.session_id)
    return Response("OK", media_type="text/plain")


@app.get("/")
async def index() -> Response:
    return Response("Workflow-Builder Generator (Gemini)", media_type="text/plain")
