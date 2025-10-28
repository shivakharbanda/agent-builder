from __future__ import annotations

import os
import re
import json
import asyncio
import uuid
from typing import Any, Literal, List, Dict, TypedDict, Optional
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

import httpx
from pydantic_ai import Agent, UnexpectedModelBehavior, RunContext, ModelRetry
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
from dq_db_manager.models.postgres import DataSourceMetadata

# Import multi-agent system
from agents.supervisor import supervisor_agent
from models.deps import SupervisorDeps, WorkflowConfig
from models.responses import WorkflowBuilderResponse


# ------------------------------------------------------------------------------
# Configuration
# ------------------------------------------------------------------------------

DB_PATH = os.getenv("DB_PATH", "messages.db")

# Django API base URL for tool calls
DJANGO_API_BASE = os.getenv("DJANGO_API_BASE", "http://localhost:8000")

# Model configuration
MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash-latest")

# Use Google API key for Generative Language API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set. Please set your Google API key in the .env file.")

provider = GoogleProvider(api_key=GOOGLE_API_KEY)

model = GoogleModel(MODEL_NAME, provider=provider)


# ------------------------------------------------------------------------------
# Type Definitions
# ------------------------------------------------------------------------------

# No longer need TypedDict - just pass session_id as string
# WorkflowBuilderDeps removed - FastAPI is now stateless


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
    """Schema inspection result with credential info and metadata from dq_db_manager"""
    credential_id: int
    credential_name: str
    database_type: str
    metadata: DataSourceMetadata


class DatabaseQueryResult(BaseModel):
    """Database query execution result"""
    columns: List[str]
    data: List[Dict[str, Any]]
    row_count: int


# ------------------------------------------------------------------------------
# Generator agent prompt: workflow structure generation
# ------------------------------------------------------------------------------

GENERATOR_PROMPT = """
You are an expert workflow builder with intelligent tools to auto-configure data processing workflows.

AVAILABLE TOOLS:
1. get_credentials(search="", category="RDBMS") - Find database credentials for current user
2. get_agents(search="") - Find AI agents for current project
3. inspect_database_schema(credential_id) - Get database tables, columns, and sample data to generate SQL queries
4. query_database(credential_id, query) - Execute SQL queries to analyze actual data (automatically limited to 1 row for safety)

GOAL: Use tools to find resources, inspect schemas, generate fully configured workflows, present preview, get confirmation, then output JSON.

CONVERSATION FLOW:
1) User describes workflow goal

2) Gather context through focused questions (1-3 questions max) IF needed:
   - What data source? (if user didn't mention)
   - What processing/analysis? (if not clear)
   - Where should output go? (if not obvious)

   Extract keywords for tool searches:
   - Data source keywords: database names, table hints, data types
   - Task keywords: action verbs (analyze, classify, transform, filter, extract, etc.)

3) Call tools WHEN you have enough context:

   get_credentials(search=""):
     WHEN: You understand what type of data source user needs
     HOW: Always call with search="" to fetch ALL available credentials
     WHY: The search parameter only does basic substring matching - you need to see all options to make intelligent choices

     After getting results:
       - Review ALL credential names and descriptions
       - Match based on user's data source requirements
       - Choose the most relevant credential

   get_agents(search=""):
     WHEN: You understand what processing/task is needed
     HOW: Always call with search="" to fetch ALL available agents
     WHY: The search parameter only does basic substring matching - you need to see all options to make intelligent choices

     After getting results:
       - Review ALL agent names, descriptions, and capabilities
       - Match based on user's task requirements
       - Choose the best fit agent

     IF exact match found:
       → Use that agent

     IF no exact match but agents exist:
       → Review ALL available agents from the tool result
       → Choose the closest match based on description/return_type/capabilities
       → Present to user: "I couldn't find a [REQUESTED_TASK] agent, but found [AGENT_NAME] which can [AGENT_CAPABILITIES]. Should I use this agent?"
       → Wait for user confirmation

     IF no agents found (empty list returned):
       → Suggest empty agent node
       → "No matching agents found. I can create the workflow with an empty agent node that you can configure later in the UI. Proceed?"

4) Present what you found from tools:
   "✓ Found credential: [CREDENTIAL_NAME] ([DATABASE_TYPE])
    ✓ Found agent: [AGENT_NAME]

    Should I inspect the database schema and create this workflow?"

5) AFTER user confirms, call inspect_database_schema:
   - Use credential_id from get_credentials() result (you already have it)
   - Call: inspect_database_schema(credential_id=the_id_from_step_3)
   - Use returned schema to generate SQL queries with real table/column names

   IMPORTANT: You do NOT have table/column names until this tool returns.
   DO NOT ask user for credential_id - you saved it from get_credentials() result.

   OPTIONAL - Call query_database to analyze actual data:
   - If you need to understand data patterns, distributions, or content to generate better SQL queries
   - Call: query_database(credential_id=credential_id, query="SELECT * FROM table_name")
   - Use returned data to inform your workflow configuration
   - The query will be automatically limited to 1 row for safety

6) Generate final JSON configuration using:
   - credential_id from get_credentials()
   - SQL query from inspect_database_schema() results
   - agent_id from get_agents()
   - All other required fields

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

ASKING vs TOOL CALLING:

ASK QUESTIONS when: You need more context to know what to search for in tools
  Examples:
  - "What data source are you working with?"
  - "What kind of processing/analysis do you need?"
  - "Where should the results be saved?"

CALL TOOLS when: You have enough context to search effectively
  Examples:
  - User mentioned their data source → call get_credentials(search="extracted_keywords")
  - User mentioned their task → call get_agents(search="task_keywords")

DO NOT ASK FOR:
  - Credential IDs (get_credentials tool provides these)
  - Agent IDs (get_agents tool provides these)
  - Table names (inspect_database_schema tool provides these)
  - Column names (inspect_database_schema tool provides these)

Keep questions to 1-3 maximum. If user provides all info upfront, skip questions and call tools immediately.

WHEN TO PRESENT PREVIEW:
Present preview when you understand:
- The core use case/purpose
- Data source (where data comes from)
- Processing steps (what happens to the data)
- Destination (where results go)

USING TOOL RESULTS - REMEMBER THE DATA:

When you call get_credentials(), you receive objects with an 'id' field.
SAVE THIS credential_id - you will need it later for inspect_database_schema().

Example:
  get_credentials() returns: [{id: 123, name: "Production DB", type: "PostgreSQL"}, ...]
  YOU NOW HAVE: credential_id = 123

When you need to call inspect_database_schema():
  USE: inspect_database_schema(credential_id=123)
  DO NOT ask user: "What is the credential ID?"
  YOU ALREADY HAVE IT from the tool result.

Same for agents:
  get_agents() returns: [{id: 456, name: "Data Classifier", ...}, ...]
  YOU NOW HAVE: agent_id = 456
  USE in final JSON: "agent_id": "456"

AGENT SELECTION STRATEGY:

SCENARIO 1 - Exact match found:
  Use the matching agent immediately

SCENARIO 2 - No exact match, but agents exist:
  - Review all available agents from get_agents() result
  - Analyze each agent's description and capabilities
  - Select the best fit based on overlap with user's task
  - Present choice: "No [USER_TASK] agent found, but [AGENT_NAME] can [RELEVANT_CAPABILITY]. Use this agent?"
  - Wait for user confirmation before proceeding

SCENARIO 3 - No agents found (empty list):
  - Present: "No matching agents found. Shall I create the workflow with an empty agent node? You can configure it later in the UI."
  - If user confirms: Use agent_id="" in the JSON configuration
  - The UI will allow manual agent selection later

DO NOT get stuck asking "what agent should I use?" - make a suggestion or offer empty node option.

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

CONFIRMATION DETECTION - Context Dependent:

After presenting the preview (showing found resources):
  User says: "yes", "okay", "sure", "proceed", "go ahead", "looks good", "correct"
  → Call inspect_database_schema() if not yet called
  → Generate the final JSON configuration

After confirming a specific resource:
  AI: "I found [CREDENTIAL_NAME], is this correct?"
  User: "yes", "correct", "that's right"
  → Proceed to next step

If tool fails and you're retrying:
  AI: [Tool failed, trying again...]
  User: "sure", "okay", "try again", "call it"
  → This means "keep trying", NOT "I accept the failure"
  → Retry the tool call

When outputting final JSON:
  Output ONLY the raw JSON with NO additional text, NO code fences, NO markdown.

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

NODE CONFIG GUIDELINES - AUTO-CONFIGURATION:

Database Node (FULLY CONFIGURED):
⚠️ CRITICAL REQUIREMENT: NEVER generate a database node without first calling inspect_database_schema(credential_id)!

{
  "type": "database",
  "config": {
    "label": "[Descriptive Label]",
    "credential_id": "X",  // ← From get_credentials() result
    "query": "SELECT column1, column2 FROM table_name WHERE condition"  // ← MUST be generated from ACTUAL inspect_database_schema() call - NEVER assume/hallucinate table/column names!
  }
}

REMINDER: You do NOT know table/column names until inspect_database_schema() returns them. Do not fabricate SQL queries.

Agent Node (FULLY CONFIGURED):
{
  "type": "agent",
  "config": {
    "label": "[Processing Task Description]",
    "agent_id": "Y",  // ← From get_agents() result
    "batch_size": "10",  // ← Smart default (5-10 for most tasks)
    "timeout": "30"  // ← Smart default (30s for most agents)
  }
}

Output Node (FULLY CONFIGURED):
{
  "type": "output",
  "config": {
    "label": "Save Results",
    "output_type": "database",  // ← Infer from context (database/file/api)
    "credential_id": "X",  // ← Reuse from input database OR ask user
    "table_name": "[task_name]_results"  // ← Auto-generate: {task}_results
  }
}

Filter Node:
{
  "type": "filter",
  "config": {
    "label": "Active Records Only",
    "conditions": [],  // User will configure in UI
    "operator": "AND"
  }
}

IMPORTANT:
- NEVER include code fences (```) around JSON output
- NEVER add explanatory text after JSON output
- Output must be valid, parseable JSON
- All node IDs must be unique (node_1, node_2, etc.)
- All edge IDs must be unique (edge_1, edge_2, etc.)
- Every edge source/target must reference existing node IDs
"""

generator_agent = Agent(
    model,
    deps_type=str,  # Just session_id string
    instructions=GENERATOR_PROMPT
)

# DIAGNOSTIC LOGGING - Agent Initialization
print(f"\n{'*'*80}")
print(f"🚀 WORKFLOW GENERATOR AGENT INITIALIZED")
print(f"   Model: {MODEL_NAME}")
print(f"   Tools: get_credentials, get_agents, inspect_database_schema, query_database")
print(f"{'*'*80}\n")


# ------------------------------------------------------------------------------
# Pydantic AI Tools - Workflow Builder Resources
# ------------------------------------------------------------------------------

@generator_agent.tool
async def get_credentials(ctx: RunContext[str], search: str = "", category: str = "RDBMS") -> list[CredentialInfo]:
    """
    Get available database credentials for the current user.

    Use this tool to find database connections that match the user's workflow requirements.

    Args:
        search: Optional search term to filter credentials by name or description
        category: Credential category (default: RDBMS for databases)

    Returns:
        List of credentials with id, name, type, and description
    """
    session_id = ctx.deps  # Just a string now

    # DIAGNOSTIC LOGGING
    print(f"\n{'='*80}")
    print(f"🔧 TOOL CALLED: get_credentials")
    print(f"   Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"   Session ID: {session_id}")
    print(f"   Parameters: search='{search}', category='{category}'")
    print(f"{'='*80}\n")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{DJANGO_API_BASE}/api/builder-tools/get_credentials/"
            params = {"session_id": session_id, "search": search, "category": category}

            print(f"   → HTTP GET {url}")
            print(f"   → Parameters: {params}")

            response = await client.get(url, params=params)

            print(f"   ← HTTP Status: {response.status_code}")
            print(f"   ← Response Body: {response.text}")

            response.raise_for_status()
            data = response.json()
            result = [CredentialInfo(**item) for item in data]

            # Log success
            print(f"✅ get_credentials SUCCESS: Found {len(result)} credentials")
            for cred in result:
                print(f"   - {cred.name} (ID: {cred.id}, Type: {cred.credential_type_name})")

            return result
    except httpx.HTTPStatusError as e:
        print(f"❌ get_credentials HTTP ERROR: {e.response.status_code}")
        print(f"   ← Response Body: {e.response.text}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error fetching credentials: {e.response.status_code}")
        else:
            # Client error - return empty list
            print(f"   Returning empty list due to client error")
            return []
    except httpx.TimeoutException:
        print(f"❌ get_credentials TIMEOUT")
        raise ModelRetry("Timeout fetching credentials. Please retry.")
    except Exception as e:
        # Log error and return empty list for other exceptions
        print(f"❌ get_credentials EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        print(f"   ← Traceback:\n{traceback.format_exc()}")
        return []


@generator_agent.tool
async def get_agents(ctx: RunContext[str], search: str = "") -> list[AgentInfo]:
    """
    Get available AI agents for the current project.

    Use this tool to find AI agents that match the workflow processing requirements.

    Args:
        search: Optional search term to filter agents by name or description

    Returns:
        List of agents with id, name, description, and return_type
    """
    session_id = ctx.deps  # Just a string now

    # DIAGNOSTIC LOGGING
    print(f"\n{'='*80}")
    print(f"🔧 TOOL CALLED: get_agents")
    print(f"   Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"   Session ID: {session_id}")
    print(f"   Parameters: search='{search}'")
    print(f"{'='*80}\n")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            url = f"{DJANGO_API_BASE}/api/builder-tools/get_agents/"
            params = {"session_id": session_id, "search": search}

            print(f"   → HTTP GET {url}")
            print(f"   → Parameters: {params}")

            response = await client.get(url, params=params)

            print(f"   ← HTTP Status: {response.status_code}")
            print(f"   ← Response Body: {response.text}")

            response.raise_for_status()
            data = response.json()
            result = [AgentInfo(**item) for item in data]

            # Log success
            print(f"✅ get_agents SUCCESS: Found {len(result)} agents")
            for agent in result:
                print(f"   - {agent.name} (ID: {agent.id})")

            return result
    except httpx.HTTPStatusError as e:
        print(f"❌ get_agents HTTP ERROR: {e.response.status_code}")
        print(f"   ← Response Body: {e.response.text}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error fetching agents: {e.response.status_code}")
        else:
            # Client error - return empty list
            print(f"   Returning empty list due to client error")
            return []
    except httpx.TimeoutException:
        print(f"❌ get_agents TIMEOUT")
        raise ModelRetry("Timeout fetching agents. Please retry.")
    except Exception as e:
        # Log error and return empty list for other exceptions
        print(f"❌ get_agents EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        print(f"   ← Traceback:\n{traceback.format_exc()}")
        return []


@generator_agent.tool
async def inspect_database_schema(ctx: RunContext[str], credential_id: int) -> SchemaInspectionResult:
    """
    Inspect database schema to understand table structure and generate SQL queries.

    Use this tool AFTER finding a credential with get_credentials() to understand
    what tables and columns are available, then generate appropriate SQL queries.

    Args:
        credential_id: ID of the database credential to inspect

    Returns:
        Schema information including tables, columns, data types, and metadata from dq_db_manager
    """
    session_id = ctx.deps  # Just a string now

    # DIAGNOSTIC LOGGING
    print(f"\n{'='*80}")
    print(f"🔧 TOOL CALLED: inspect_database_schema")
    print(f"   Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"   Session ID: {session_id}")
    print(f"   Parameters: credential_id={credential_id}")
    print(f"{'='*80}\n")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{DJANGO_API_BASE}/api/builder-tools/inspect_schema/"
            json_body = {"credential_id": credential_id, "session_id": session_id}

            print(f"   → HTTP POST {url}")
            print(f"   → JSON Body: {json_body}")

            response = await client.post(url, json=json_body)

            print(f"   ← HTTP Status: {response.status_code}")
            print(f"   ← Response Body: {response.text[:1000]}")  # Limit to first 1000 chars

            response.raise_for_status()
            data = response.json()
            result = SchemaInspectionResult(**data)

            # Log success
            print(f"✅ inspect_database_schema SUCCESS")
            print(f"   Credential: {result.credential_name} (ID: {result.credential_id})")
            print(f"   Database Type: {result.database_type}")
            if result.metadata.tables:
                print(f"   Tables found: {len(result.metadata.tables)}")
                for table in result.metadata.tables[:3]:  # Show first 3 tables
                    print(f"     - {table.table_name} ({len(table.columns)} columns)")

            return result
    except httpx.HTTPStatusError as e:
        print(f"❌ inspect_database_schema HTTP ERROR: {e.response.status_code}")
        print(f"   ← Response Body: {e.response.text}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error inspecting schema: {e.response.status_code}")
        elif e.response.status_code == 404:
            raise ModelRetry(f"Credential {credential_id} not found. Please verify the credential ID.")
        else:
            raise ModelRetry(f"Cannot inspect schema for credential {credential_id}: {e.response.text}")
    except httpx.TimeoutException:
        print(f"❌ inspect_database_schema TIMEOUT")
        raise ModelRetry("Schema inspection timeout. Database may be slow or unavailable. Please retry.")
    except Exception as e:
        # Log and raise retry for any other exception
        print(f"❌ inspect_database_schema EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        print(f"   ← Traceback:\n{traceback.format_exc()}")
        raise ModelRetry(f"Error inspecting database schema: {str(e)}")


@generator_agent.tool
async def query_database(ctx: RunContext[str], credential_id: int, query: str) -> DatabaseQueryResult:
    """
    Execute a SQL query to analyze data from the database.

    Use this tool AFTER finding a credential with get_credentials() to run SQL queries
    and inspect actual data. This helps understand data patterns, distributions, and content
    to generate better workflow configurations.

    Args:
        credential_id: ID of the database credential to query against
        query: SQL query to execute (will be automatically limited to 1 row for safety)

    Returns:
        Query results including columns, sample data, and row count
    """
    session_id = ctx.deps  # Just a string now

    # DIAGNOSTIC LOGGING
    print(f"\n{'='*80}")
    print(f"🔧 TOOL CALLED: query_database")
    print(f"   Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"   Session ID: {session_id}")
    print(f"   Parameters: credential_id={credential_id}, query='{query}'")
    print(f"{'='*80}\n")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"{DJANGO_API_BASE}/api/builder-tools/test_query/"
            json_body = {
                "credential_id": credential_id,
                "query": query,
                "session_id": session_id
            }

            print(f"   → HTTP POST {url}")
            print(f"   → JSON Body: {json_body}")

            response = await client.post(url, json=json_body)

            print(f"   ← HTTP Status: {response.status_code}")
            print(f"   ← Response Body: {response.text[:500]}")  # Limit to first 500 chars

            response.raise_for_status()
            data = response.json()
            result = DatabaseQueryResult(**data)

            # Log success
            print(f"✅ query_database SUCCESS")
            print(f"   Columns: {result.columns}")
            print(f"   Row count: {result.row_count}")
            if result.data:
                print(f"   Sample data: {result.data[0] if len(result.data) > 0 else 'No data'}")

            return result
    except httpx.HTTPStatusError as e:
        print(f"❌ query_database HTTP ERROR: {e.response.status_code}")
        print(f"   ← Response Body: {e.response.text}")
        if e.response.status_code >= 500:
            raise ModelRetry(f"Server error executing query: {e.response.status_code}")
        elif e.response.status_code == 404:
            raise ModelRetry(f"Credential {credential_id} not found. Please verify the credential ID.")
        else:
            raise ModelRetry(f"Cannot execute query for credential {credential_id}: {e.response.text}")
    except httpx.TimeoutException:
        print(f"❌ query_database TIMEOUT")
        raise ModelRetry("Query execution timeout. Query may be too complex or database may be slow. Please retry.")
    except Exception as e:
        # Log and raise retry for any other exception
        print(f"❌ query_database EXCEPTION: {type(e).__name__}: {e}")
        import traceback
        print(f"   ← Traceback:\n{traceback.format_exc()}")
        raise ModelRetry(f"Error executing database query: {str(e)}")


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
    current_config: Optional[dict] = None  # NEW: current workflow state for incremental/edit mode


class SessionScopedRequest(BaseModel):
    session_id: str


class NewSessionRequest(BaseModel):
    session_id: str  # Now receives session_id from Django


class NewSessionResponse(BaseModel):
    session_id: str
    status: str


# ============================================================================
# Session Storage (Stateless - only usage tracking)
# ============================================================================

SESSION_STORAGE: Dict[str, Dict[str, Any]] = {}


async def store_session_context(session_id: str) -> None:
    """Store minimal session context - just usage tracking"""
    SESSION_STORAGE[session_id] = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "usage": {
            "requests": 0,
            "request_tokens": 0,
            "response_tokens": 0,
            "total_tokens": 0
        }
    }


async def get_session_context(session_id: str) -> Dict[str, Any]:
    """Retrieve session context"""
    return SESSION_STORAGE.get(session_id, {})


async def update_session_usage(session_id: str, requests: int, request_tokens: int, response_tokens: int, total_tokens: int) -> None:
    """Update session usage statistics"""
    if session_id in SESSION_STORAGE:
        usage = SESSION_STORAGE[session_id]["usage"]
        usage["requests"] += requests
        usage["request_tokens"] += request_tokens
        usage["response_tokens"] += response_tokens
        usage["total_tokens"] += total_tokens


# ------------------------------------------------------------------------------
# Routes
# ------------------------------------------------------------------------------

@app.get("/healthz")
async def healthz() -> Response:
    return Response("ok", media_type="text/plain")


@app.post("/session/", response_model=NewSessionResponse)
async def new_session(body: NewSessionRequest) -> NewSessionResponse:
    """
    Initialize a FastAPI session with session_id from Django.

    FastAPI is now stateless - it receives pre-registered session_id from Django.
    """
    session_id = body.session_id
    await store_session_context(session_id)
    return NewSessionResponse(session_id=session_id, status="initialized")


@app.post("/generate/")
async def generate_workflow(body: GenerateRequest) -> StreamingResponse:
    """
    INCREMENTAL workflow generation using multi-agent system with structured output.

    NEW FEATURES:
    - Accepts current_config for incremental/edit mode
    - Uses supervisor + worker multi-agent system
    - Returns structured responses (WorkflowBuilderResponse)
    - Supports one-change-at-a-time workflow building

    OLD (deprecated but kept for now): generator_agent for full workflow generation
    """
    prompt = body.prompt
    session_id = body.session_id
    current_config = body.current_config

    # DIAGNOSTIC LOGGING - Endpoint Entry
    print(f"\n{'#'*80}")
    print(f"📥 /generate/ ENDPOINT CALLED (MULTI-AGENT + STRUCTURED)")
    print(f"   Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"   Session ID: {session_id}")
    print(f"   Prompt: {prompt[:100]}{'...' if len(prompt) > 100 else ''}")
    print(f"   Current Config: {'Present (edit mode)' if current_config else 'None (new workflow)'}")
    print(f"{'#'*80}\n")

    async def stream():
        # Immediately echo the user message so the client can render it.
        yield json.dumps({"role": "user", "timestamp": now_iso(), "content": prompt}).encode("utf-8") + b"\n"

        # Load message history
        messages = await load_messages(session_id)
        print(f"📚 Loaded {len(messages)} messages from history")

        # Load pending tasks from Django database
        pending_tasks = []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                url = f"{DJANGO_API_BASE}/api/builder-tools/get_session_tasks/"
                params = {"session_id": session_id}
                print(f"📋 Loading pending tasks from Django: {url}")
                response = await client.get(url, params=params)

                if response.status_code == 200:
                    data = response.json()
                    pending_tasks = data.get("tasks", [])
                    print(f"✅ Loaded {len(pending_tasks)} pending tasks")
                else:
                    print(f"⚠️ Could not load tasks (status {response.status_code}), using empty list")
        except Exception as e:
            print(f"⚠️ Error loading tasks: {e}, using empty list")

        # Build SupervisorDeps with current config and pending tasks
        workflow_config = WorkflowConfig(**(current_config or {}))
        deps = SupervisorDeps(
            session_id=session_id,
            current_config=workflow_config,
            pending_tasks=pending_tasks
        )

        print(f"👔 Starting supervisor_agent with:")
        print(f"   - Session ID: {session_id}")
        print(f"   - Mode: {'EDIT' if deps.is_editing else 'NEW'}")
        print(f"   - Current nodes: {len(workflow_config.nodes)}")
        print(f"   - Current edges: {len(workflow_config.edges)}")
        print(f"   - Pending tasks: {len(deps.pending_tasks)}")

        # Run supervisor agent (non-streaming for structured output)
        # NOTE: With output_type, Pydantic AI builds structured data internally
        # and returns it in result.output after completion
        print(f"🤖 Running supervisor agent (awaiting structured response)...")
        result = await supervisor_agent.run(prompt, message_history=messages, deps=deps)

        # Get final structured response
        structured_response = result.output  # This is a WorkflowBuilderResponse object

        print(f"✅ Supervisor completed successfully")
        print(f"📤 Structured Response:")
        print(f"   Action: {structured_response.action_type}")
        print(f"   Message: {structured_response.message[:80]}...")

        # Yield structured response as JSON
        yield json.dumps({
            "role": "assistant",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "structured": True,
            "response": structured_response.model_dump()
        }).encode("utf-8") + b"\n"

        # Persist new messages (both the user request and the model response).
        await add_messages_blob(session_id, result.new_messages_json())
        print(f"💾 Persisted new messages to database")

        # Save updated pending tasks back to Django database
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                url = f"{DJANGO_API_BASE}/api/builder-tools/save_session_tasks/"
                json_body = {
                    "session_id": session_id,
                    "tasks": deps.pending_tasks
                }
                print(f"📋 Saving {len(deps.pending_tasks)} pending tasks to Django")
                response = await client.post(url, json=json_body)

                if response.status_code == 200:
                    print(f"✅ Tasks saved successfully")
                else:
                    print(f"⚠️ Failed to save tasks (status {response.status_code})")
        except Exception as e:
            print(f"⚠️ Error saving tasks: {e}")

        # Track usage statistics
        usage = result.usage()
        await update_session_usage(
            session_id,
            requests=usage.requests,
            request_tokens=usage.request_tokens,
            response_tokens=usage.response_tokens,
            total_tokens=usage.total_tokens
        )

        print(f"📊 Usage: {usage.request_tokens} request tokens, {usage.response_tokens} response tokens")
        print(f"{'#'*80}\n")

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


@app.get("/test-tools/{session_id}")
async def test_tools(session_id: str) -> Response:
    """
    Test endpoint to manually verify tool execution.
    This will directly call each tool to verify they work independently of the LLM.
    """
    import traceback

    results = {
        "session_id": session_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "tests": {}
    }

    # Test 1: get_credentials
    print(f"\n{'='*80}")
    print(f"🧪 MANUAL TEST: get_credentials")
    print(f"{'='*80}\n")
    try:
        # Create a fake RunContext with session_id as deps
        class FakeContext:
            def __init__(self, deps):
                self.deps = deps

        ctx = FakeContext(session_id)
        credentials = await get_credentials(ctx, search="", category="RDBMS")
        results["tests"]["get_credentials"] = {
            "status": "success",
            "result_count": len(credentials),
            "credentials": [{"id": c.id, "name": c.name, "type": c.credential_type_name} for c in credentials]
        }
        print(f"✅ Test passed: Found {len(credentials)} credentials")
    except Exception as e:
        results["tests"]["get_credentials"] = {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        print(f"❌ Test failed: {e}")

    # Test 2: get_agents
    print(f"\n{'='*80}")
    print(f"🧪 MANUAL TEST: get_agents")
    print(f"{'='*80}\n")
    try:
        ctx = FakeContext(session_id)
        agents = await get_agents(ctx, search="")
        results["tests"]["get_agents"] = {
            "status": "success",
            "result_count": len(agents),
            "agents": [{"id": a.id, "name": a.name} for a in agents]
        }
        print(f"✅ Test passed: Found {len(agents)} agents")
    except Exception as e:
        results["tests"]["get_agents"] = {
            "status": "error",
            "error": str(e),
            "traceback": traceback.format_exc()
        }
        print(f"❌ Test failed: {e}")

    # Test 3: inspect_database_schema (only if we found credentials)
    if results["tests"].get("get_credentials", {}).get("result_count", 0) > 0:
        first_cred_id = results["tests"]["get_credentials"]["credentials"][0]["id"]
        print(f"\n{'='*80}")
        print(f"🧪 MANUAL TEST: inspect_database_schema (credential_id={first_cred_id})")
        print(f"{'='*80}\n")
        try:
            ctx = FakeContext(session_id)
            schema = await inspect_database_schema(ctx, credential_id=first_cred_id)
            results["tests"]["inspect_database_schema"] = {
                "status": "success",
                "credential_id": first_cred_id,
                "credential_name": schema.credential_name,
                "database_type": schema.database_type,
                "table_count": len(schema.metadata.tables) if schema.metadata.tables else 0
            }
            print(f"✅ Test passed: Inspected schema successfully")
        except Exception as e:
            results["tests"]["inspect_database_schema"] = {
                "status": "error",
                "error": str(e),
                "traceback": traceback.format_exc()
            }
            print(f"❌ Test failed: {e}")
    else:
        results["tests"]["inspect_database_schema"] = {
            "status": "skipped",
            "reason": "No credentials found to test with"
        }

    return Response(json.dumps(results, indent=2), media_type="application/json")


@app.get("/")
async def index() -> Response:
    return Response("Workflow-Builder Generator (Gemini)", media_type="text/plain")
