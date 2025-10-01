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
# Meta-agent prompt: asks exactly one question at a time and outputs raw JSON at the end
# ------------------------------------------------------------------------------

SYSTEM_PROMPT = (
    "You are a meta-agent that interviews the user to build an agent configuration.\n"
    "Collect, in this order, asking exactly ONE question per turn:\n"
    "1) return_type: ask whether they want a 'conversational' agent or a 'workflow' (deterministic) agent.\n"
    "   - If conversational, set return_type='unstructured'.\n"
    "   - If workflow/deterministic, set return_type='structured'.\n"
    "2) name: ask for a concise agent name.\n"
    "3) description: ask for a one-sentence description.\n"
    "4) system_prompt: ask for the system/role prompt. Allow placeholders written as {placeholder_name}.\n"
    "5) user_prompt: ask for a representative user prompt template. Allow placeholders written as {placeholder_name}.\n"
    "6) If return_type is 'structured', gather a valid JSON Schema for the output with:\n"
    "   - type='object'\n"
    "   - properties: an object of fields\n"
    "   - required: array of required field names\n"
    "   If user prefers, draft a minimal JSON Schema and confirm it.\n\n"
    "Validation rules:\n"
    "- If a reply is invalid or off-topic, politely re-ask with a brief hint.\n"
    "- Keep each question short.\n\n"
    "Finalization:\n"
    "When (and only when) all fields are collected, output a SINGLE JSON object (no code fences, no commentary) with keys:\n"
    "{\n"
    '  "name": string,\n'
    '  "description": string,\n'
    '  "return_type": "structured" | "unstructured",\n'
    '  "prompts": [\n'
    '    {"prompt_type": "system", "content": string, "placeholders": object},\n'
    '    {"prompt_type": "user", "content": string, "placeholders": object}\n'
    "  ],\n"
    '  "schema_definition": object // include ONLY if return_type == "structured"\n'
    "}\n"
    "Placeholders: infer keys from {curly_braces} in each prompt and include a map\n"
    'like {"placeholder_name": "brief description of what to provide"}.\n'
    "Output only that JSON object at the end—no extra text."
)

# Generator system prompt for focused conversational agent creation
GENERATOR_PROMPT = (
    "You are an expert agent configurator that helps users create agent configurations through focused questions.\n\n"
    "GOAL: Ask targeted questions to understand what the user wants, present a preview, get confirmation, then output the JSON config.\n\n"
    "CONVERSATION FLOW:\n"
    "1) User gives initial requirement/use case\n"
    "2) Ask clarifying questions ONLY about unclear or missing details:\n"
    "   - What specific inputs/outputs are needed?\n"
    "   - What's the context/domain?\n"
    "   - Are there specific constraints or requirements?\n"
    "   - Should it return structured data or conversational responses?\n"
    "3) When you have enough info, present a clear preview and ask for confirmation\n"
    "4) ONLY after user confirms (yes/okay/looks good/etc), output the raw JSON\n\n"
    "QUESTION STRATEGY:\n"
    "- Ask 1-3 focused questions max\n"
    "- Be direct and specific\n"
    "- Make reasonable assumptions when possible\n"
    "- Don't ask about obvious things\n\n"
    "WHEN TO PRESENT PREVIEW:\n"
    "Present preview when you understand:\n"
    "- The core use case/purpose\n"
    "- Input/output requirements\n"
    "- Whether structured or conversational output is needed\n\n"
    "PREVIEW FORMAT:\n"
    "Present the configuration clearly:\n"
    "---\n"
    "Perfect! I'll create an agent with this configuration:\n\n"
    "**Agent Name:** [name]\n"
    "**Description:** [description]\n"
    "**Return Type:** [structured/unstructured]\n"
    "**Input:** [what user provides]\n"
    "**Output:** [what agent returns]\n"
    "---\n"
    "Does this look good? Should I proceed with this configuration?\n\n"
    "CONFIRMATION DETECTION:\n"
    "If user responds affirmatively (yes, okay, ok, sure, looks good, perfect, go ahead, proceed, etc.),\n"
    "IMMEDIATELY output ONLY the raw JSON with NO additional text.\n\n"
    "FINAL OUTPUT (only after user confirmation):\n"
    "Output ONLY the JSON object (no markdown, no code fences, no extra text):\n"
    "{\n"
    '  \"name\": string,\n'
    '  \"description\": string,\n'
    '  \"return_type\": \"structured\" | \"unstructured\",\n'
    '  \"prompts\": [\n'
    '    {\"prompt_type\": \"system\", \"content\": string, \"placeholders\": object},\n'
    '    {\"prompt_type\": \"user\", \"content\": string, \"placeholders\": object}\n'
    "  ],\n"
    '  \"schema_definition\": object   // ONLY if return_type==\"structured\"\n'
    "}\n\n"
    "IMPORTANT: Use double curly braces {{placeholder_name}} for placeholders in prompt content.\n"
    "Include placeholders map: {\"key\": \"description of what to provide\"}.\n"
    "For structured agents, create practical JSON Schema with type='object', properties, required fields."
)

meta_agent = Agent(model, system_prompt=SYSTEM_PROMPT)
generator_agent = Agent(model, system_prompt=GENERATOR_PROMPT)


# ------------------------------------------------------------------------------
# FastAPI app + CORS
# ------------------------------------------------------------------------------

app = fastapi.FastAPI(title="Agent-Builder Meta-Agent (Gemini)")

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


def extract_and_validate_json(text: str) -> dict | None:
    """
    Deterministically extract and validate JSON from text.
    Handles both raw JSON and markdown code fence wrapped JSON.
    Returns parsed dict if valid agent config, None otherwise.
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

        # Validate it's an agent config with required fields
        if not isinstance(payload, dict):
            return None

        # Check required fields
        if not (isinstance(payload.get("name"), str) and payload["name"].strip()):
            return None
        if not (isinstance(payload.get("description"), str) and payload["description"].strip()):
            return None
        if payload.get("return_type") not in ("structured", "unstructured"):
            return None
        if not (isinstance(payload.get("prompts"), list) and len(payload["prompts"]) >= 2):
            return None

        return payload

    except (json.JSONDecodeError, KeyError, TypeError):
        return None


PLACEHOLDER_RE = re.compile(r"\{([a-zA-Z_][a-zA-Z0-9_]*)\}")

def infer_placeholders_map(prompt_text: str) -> Dict[str, str]:
    keys = list(dict.fromkeys(PLACEHOLDER_RE.findall(prompt_text or "")))
    return {k: f"Provide a valid value for '{k}'" for k in keys}


def ensure_placeholders(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Safety net: if the model forgot placeholders maps, fill them from {curly_braces}.
    """
    if "prompts" not in payload or not isinstance(payload["prompts"], list):
        return payload
    for p in payload["prompts"]:
        if isinstance(p, dict):
            content = p.get("content", "")
            placeholders = p.get("placeholders")
            if not isinstance(placeholders, dict):
                p["placeholders"] = infer_placeholders_map(content)
    return payload


# ------------------------------------------------------------------------------
# API models
# ------------------------------------------------------------------------------

class ChatRequest(BaseModel):
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


class GenerateSessionRequest(BaseModel):
    prompt: str
    session_id: str


@app.post("/generate/")
async def generate_chat(body: GenerateSessionRequest) -> StreamingResponse:
    """
    Conversational agent generation: ask focused questions, then output final config JSON.
    Uses session-based conversation like /chat/ but with generator agent.
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
            payload = extract_and_validate_json(candidate)

            if payload:
                # Ensure placeholders maps exist (safety net)
                payload = ensure_placeholders(payload)

                # If structured, validate schema_definition
                if payload["return_type"] == "structured":
                    schema = payload.get("schema_definition")
                    if not isinstance(schema, dict) or schema.get("type") != "object" or "properties" not in schema:
                        return Response(
                            "Final JSON is present but schema_definition is missing/invalid.",
                            media_type="text/plain",
                            status_code=422,
                        )

                # Valid config found
                return Response(json.dumps(payload, indent=2), media_type="application/json")

    # No valid config found in any message
    return Response("Not finalized yet.", media_type="text/plain", status_code=202)


@app.post("/reset/")
async def reset(body: SessionScopedRequest) -> Response:
    await reset_messages(body.session_id)
    return Response("OK", media_type="text/plain")


@app.get("/")
async def index() -> Response:
    return Response("Agent-Builder Meta-Agent (Gemini)", media_type="text/plain")


@app.get("/chat/")
async def get_chat(session_id: str) -> Response:
    msgs = await load_messages(session_id)
    lines = [json.dumps(to_chat_message(m)).encode("utf-8") for m in msgs]
    return Response(b"\n".join(lines), media_type="text/plain")


@app.post("/chat/")
async def post_chat(body: ChatRequest) -> StreamingResponse:
    prompt = body.prompt
    session_id = body.session_id

    async def stream():
        # Immediately echo the user message so the client can render it.
        yield json.dumps({"role": "user", "timestamp": now_iso(), "content": prompt}).encode("utf-8") + b"\n"

        messages = await load_messages(session_id)

        # Run the agent with full history and stream model output.
        async with meta_agent.run_stream(prompt, message_history=messages) as result:
            async for text in result.stream_output(debounce_by=0.01):
                m = ModelResponse(parts=[TextPart(text)], timestamp=result.timestamp())
                yield json.dumps(to_chat_message(m)).encode("utf-8") + b"\n"

        # Persist new messages (both the user request and the model response).
        await add_messages_blob(session_id, result.new_messages_json())

    return StreamingResponse(stream(), media_type="text/plain")


@app.get("/finalize/")
async def finalize(session_id: str) -> Response:
    """
    Attempts to parse the last assistant message as the final JSON config.
    Returns 202 if not finalized yet, 200 with JSON if valid config found.
    """
    messages = await load_messages(session_id)
    if not messages:
        return Response("Not finalized yet.", media_type="text/plain", status_code=202)

    # Find last assistant message and try to extract valid JSON
    for m in reversed(messages):
        if isinstance(m, ModelResponse) and isinstance(m.parts[0], TextPart):
            candidate = m.parts[0].content
            payload = extract_and_validate_json(candidate)

            if payload:
                # Ensure placeholders maps exist (safety net)
                payload = ensure_placeholders(payload)

                # If structured, validate schema_definition
                if payload["return_type"] == "structured":
                    schema = payload.get("schema_definition")
                    if not isinstance(schema, dict) or schema.get("type") != "object" or "properties" not in schema:
                        return Response(
                            "Final JSON is present but schema_definition is missing/invalid.",
                            media_type="text/plain",
                            status_code=422,
                        )

                # Valid config found
                return Response(json.dumps(payload, indent=2), media_type="application/json")

    # No valid config found in any message
    return Response("Not finalized yet.", media_type="text/plain", status_code=202)