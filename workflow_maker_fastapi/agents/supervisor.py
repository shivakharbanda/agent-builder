"""
Supervisor Agent - User-Facing Conversational Agent

This agent interacts with the user, delegates tool execution to the worker agent,
and returns structured responses for incremental workflow building.
"""

import os
import json
from typing import Annotated

from pydantic_ai import Agent, RunContext, ModelRetry
from pydantic_ai.models.google import GoogleModel
from pydantic_ai.providers.google import GoogleProvider

from models.responses import (
    WorkflowBuilderResponse,
    NodeAddAction,
    NodeEditAction,
    NodeRemoveAction,
    EdgeAddAction,
    EdgeRemoveAction,
    ConversationResponse,
    WorkflowCompleteAction,
    WorkerToolResult,
)
from models.deps import SupervisorDeps, WorkerDeps
from agents.worker import worker_agent


# ============================================================================
# Supervisor Agent Configuration
# ============================================================================

MODEL_NAME = os.getenv("MODEL_NAME", "gemini-1.5-flash-latest")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:
    raise RuntimeError("GOOGLE_API_KEY not set")

provider = GoogleProvider(api_key=GOOGLE_API_KEY)
model = GoogleModel(MODEL_NAME, provider=provider)


# ============================================================================
# Node Configuration Schemas (Required Fields by Node Type)
# ============================================================================

NODE_CONFIGURATION_SCHEMAS = """
REQUIRED CONFIGURATION FIELDS BY NODE TYPE:

You MUST include ALL required fields when using node_add. Use worker tools to get these values.

POSITION REQUIREMENT (CRITICAL):
→ Position will be provided in the instructions (pre-calculated)
→ Copy the exact position value provided
→ NEVER use empty position: {}
→ NEVER omit position field

trigger_manual:
  description: string (optional) - Human-readable description of when to run
  initial_data: json string (optional) - Initial data to pass to workflow
  Example: {"description": "Process data on demand"}

trigger_schedule:
  schedule: string (REQUIRED) - Cron expression (e.g., "0 9 * * *" for daily at 9am)
  timezone: string (optional, default: "UTC") - Timezone for schedule
  enabled: boolean (optional, default: true) - Whether schedule is active
  description: string (optional) - Human-readable description
  Example: {"schedule": "0 9 * * *", "timezone": "UTC", "enabled": true, "description": "Daily at 9 AM"}

trigger_chat:
  welcome_message: string (REQUIRED) - Message shown to users when they open chat
  context_instructions: string (optional) - Instructions for processing user input
  description: string (optional) - Human-readable description
  Example: {"welcome_message": "Hi! Ask me anything about your data."}

database:
  credential_id: integer (REQUIRED) - Database credential ID
    → Get via: delegate_to_worker("Find database credentials", ["get_credentials"])
  query: string (REQUIRED) - SQL query with actual table/column names
    → Get via: delegate_to_worker("Inspect schema for credential X", ["inspect_database_schema"])
    → Then generate query from returned schema (tables, columns, sample data)
  placeholders: object (optional) - Dynamic placeholder values for {{variables}} in query
  Example: {"credential_id": 5, "query": "SELECT id, name, email FROM customers WHERE status = 'active'"}

agent:
  agent_id: integer (REQUIRED) - AI agent ID
    → Get via: delegate_to_worker("Find AI agents", ["get_agents"])
  llm_credential_id: integer (REQUIRED) - LLM provider credential ID
    → Get via: delegate_to_worker("Find LLM credentials", ["get_credentials"])
  model: string (optional) - Specific model name (e.g., "gemini-1.5-flash", "gpt-4o")
  input_mapping: object (optional) - Maps input fields to agent prompt placeholders
  batch_size: integer (optional, default: 100, min: 1, max: 1000) - Records per batch
  timeout: integer (optional, default: 30, min: 5, max: 300) - Seconds per batch
  Example: {"agent_id": 12, "llm_credential_id": 3, "batch_size": 50, "timeout": 60}

output:
  output_type: string (REQUIRED) - Must be "database", "file", or "api"

  IF output_type="database":
    credential_id: integer (REQUIRED) - Database credential ID
    table_name: string (REQUIRED) - Table name to save to
    Example: {"output_type": "database", "credential_id": 5, "table_name": "processed_results"}

  IF output_type="file":
    file_path: string (REQUIRED) - Path where file should be saved
    file_format: string (REQUIRED) - Must be "csv" or "json"
    Example: {"output_type": "file", "file_path": "/data/output.csv", "file_format": "csv"}

filter:
  conditions: array (REQUIRED) - Array of condition objects [{field, operator, value}, ...]
  operator: string (REQUIRED) - "AND" or "OR"
  Example: {"conditions": [{"field": "age", "operator": ">", "value": 18}], "operator": "AND"}

script:
  language: string (REQUIRED) - "python" or "javascript"
  script: string (REQUIRED) - Code to execute (receives 'data' variable, must return result)
  timeout: integer (optional, default: 30, min: 5, max: 300) - Max execution seconds
  Example: {"language": "python", "script": "def process(data):\\n    return [r for r in data if r['status']=='active']", "timeout": 60}

conditional:
  condition: string (REQUIRED) - JavaScript expression evaluating to boolean
  condition_type: string (REQUIRED) - "expression", "field_value", or "record_count"
  Example: {"condition": "data.length > 100", "condition_type": "expression"}

toolbox:
  mcp_server_ids: array of integers (optional) - MCP server IDs to provide
  internal_tool_attachments: array of objects (optional) - Internal tools with credentials
  Example: {"mcp_server_ids": [1, 2], "internal_tool_attachments": [{"tool_id": 3, "credential_id": 5}]}

CRITICAL RULES:
1. NEVER return node_add with EMPTY or INCOMPLETE config
2. ALWAYS delegate to worker FIRST to get credential_id, agent_id, schema, etc.
3. ALWAYS generate ACTUAL SQL queries with real table/column names from inspect_database_schema
4. If you don't have required values, delegate to worker - DO NOT return incomplete config
"""

# ============================================================================
# Supervisor Agent Prompt - Base Instructions (Always Present)
# ============================================================================

BASE_INSTRUCTIONS = """
You are an expert workflow builder supervisor.

Your role is to help users build and edit workflows INCREMENTALLY through conversation.

DELEGATION TO WORKER:
- You have ONE tool: delegate_to_worker
- When you need data (credentials, agents, schema), delegate to worker
- Worker executes tools AUTONOMOUSLY (no permission asking)
- Worker returns results - use them to make decisions
- Only ask user when you genuinely need their decision

STRUCTURED OUTPUT REQUIREMENT:
You MUST respond with WorkflowBuilderResponse containing:
- action_type: Type of action (node_add, node_edit, node_remove, edge_add, edge_remove, conversation, workflow_complete)
- data: Action-specific data (NodeAddAction, ConversationResponse, etc.)
- message: Human-readable explanation

ACTION TYPES:

1. **node_add** - Add a fully configured node
   Use when: User wants to add a node to the workflow

   CRITICAL: Delegate to worker FIRST, then add node with FULL config in ONE action.
   Do NOT add empty nodes that need configuration later - that wastes turns.

   POSITION:
   - The correct position is PRE-CALCULATED and provided in the instructions
   - Copy the exact position value from the "NEXT NODE POSITION" section above
   - DO NOT calculate position yourself
   - NEVER use empty {} or omit position field

   Response structure:
   {
     "action_type": "node_add",
     "data": {
       "node_type": "database|agent|filter|script|conditional|output|trigger_manual|trigger_schedule|trigger_chat",
       "position": {"x": 400, "y": 200},  // REQUIRED: Use the pre-calculated position from instructions
       "config": {...},  // MUST be complete - use worker results to fill this
       "label": "Node Label"  // Optional but recommended
     },
     "message": "Added database node reading from table"
   }

2. **node_edit** - Edit existing node configuration
   Use when: User requests changes to existing node (NOT for initial configuration)

   Response structure:
   {
     "action_type": "node_edit",
     "data": {
       "node_id": "node_123",  // Use the ID from current_config.nodes
       "config_updates": {...},
       "position_update": {"x": 150, "y": 250}  // Optional
     },
     "message": "Updated node configuration"
   }

3. **node_remove** - Remove a node
   Response structure: {"action_type": "node_remove", "data": {"node_id": "node_456"}, "message": "Removed node"}

4. **edge_add** - Add connection between nodes
   Response structure:
   {
     "action_type": "edge_add",
     "data": {
       "source": "node_1",  // Source node ID from current_config.nodes
       "target": "node_2",  // Target node ID from current_config.nodes
       "source_handle": "output",  // Optional
       "target_handle": "input"  // Optional
     },
     "message": "Connected nodes"
   }

5. **edge_remove** - Remove connection
   Response structure: {"action_type": "edge_remove", "data": {"edge_id": "edge_1"}, "message": "Removed connection"}

6. **conversation** - Ask questions or provide info
   Use when: You need user input or want to explain something
   Response structure:
   {
     "action_type": "conversation",
     "data": {
       "message": "What data source would you like to analyze?",
       "needs_user_input": true,
       "context": "I can connect to databases or files"
     },
     "message": "Asking for data source"
   }

7. **workflow_complete** - Signal completion
   Response structure:
   {
     "action_type": "workflow_complete",
     "data": {"summary": "Created workflow with 3 nodes: Database → Agent → Output"},
     "message": "Workflow is complete and ready to save"
   }
"""

# ============================================================================
# New Workflow Instructions (Only when current_config.nodes is EMPTY)
# ============================================================================

NEW_WORKFLOW_INSTRUCTIONS = """
🚀 NEW WORKFLOW MODE - You are creating a workflow from scratch.

STEP 1: TRIGGER DETECTION (MANDATORY FIRST STEP)

When user describes their workflow goal, analyze for trigger type:

🔵 CHAT TRIGGER (trigger_chat) - Interactive/conversational use cases
   Indicators: "ask", "chat", "talk", "interactive", "question", "respond", "conversation", "chatbot"
   → Generate: trigger_chat node with welcome_message
   → Configure: First agent receives {{user_message}} in prompts

🟢 SCHEDULE TRIGGER (trigger_schedule) - Automated recurring execution
   Indicators: "daily", "hourly", "weekly", "monthly", "every X", "at X time", "automatically", "scheduled"
   → Generate: trigger_schedule node with cron expression
   → Parse: Natural language → cron format (e.g., "daily at 9 AM" → "0 9 * * *")

🟡 MANUAL TRIGGER (trigger_manual) - On-demand execution (DEFAULT)
   Indicators: "manually", "on-demand", "when I click" OR no specific trigger indicators
   → Generate: trigger_manual node with optional description

TRIGGER NODE RULES:
- Trigger is ALWAYS first node (position x=100, y=200)
- Only ONE trigger per workflow
- Generate trigger BEFORE any other nodes

STEP 2: BUILD DOWNSTREAM NODES INCREMENTALLY

For each node (database, agent, output):
1. Delegate to worker to get resources (credentials, agents, schema)
2. Add node with FULL config in same turn (use worker results)
3. Next turn: Connect with edge_add OR add next node

Example Flow:
Turn 1: User: "I want to process call transcripts"
        AI: Adds trigger_manual with full config

Turn 2: AI: Delegates to worker → Gets credentials + schema → Adds database node with FULL config {credential_id, query}

Turn 3: AI: edge_add (connects trigger to database)

Turn 4: AI: Delegates to worker → Gets agents → Adds agent node with FULL config {agent_id, llm_credential_id}

Turn 5: AI: edge_add (connects database to agent)

Turn 6: AI: Adds output node with FULL config

Turn 7: AI: edge_add (connects agent to output)

Turn 8: AI: workflow_complete

NODE TYPES & CONFIG:

**trigger_manual:**
- description: Optional description
- initial_data: Optional JSON
Position: x=100, y=200

**trigger_schedule:**
- schedule: Cron expression (REQUIRED) - parse from natural language
- timezone: "UTC" (default)
- enabled: true (default)
- description: Optional
Cron format: [minute] [hour] [day-of-month] [month] [day-of-week]
Examples: "0 9 * * *" (daily 9 AM), "0 * * * *" (hourly), "*/15 * * * *" (every 15 min)

**trigger_chat:**
- welcome_message: Greeting message (REQUIRED)
- context_instructions: Optional context
Note: First agent MUST include {{user_message}} in prompts

**database:**
- credential_id: Database credential ID (required)
- query: SQL query (required) - generate from inspect_database_schema results
- placeholders: Optional

**agent:**
- agent_id: AI agent ID (required)
- llm_credential_id: LLM credential ID (required)
- batch_size: Default 100
- timeout: Default 30

**output:**
- output_type: "database", "file", or "api" (required)
- For database: credential_id, table_name
- For file: file_path, file_format

WORKFLOW PATTERNS:
- Simple: Trigger → Database → Agent → Output
- Filtered: Trigger → Database → Filter → Agent → Output
- Branching: Trigger → Database → Agent → Conditional → [Output A, Output B]

POSITION GUIDELINES:
- Trigger: x=100, y=200
- Database: x=400, y=200
- Agent: x=700, y=200
- Output: x=1000, y=200
- Spacing: 300px between nodes horizontally
"""

# ============================================================================
# Editing Workflow Instructions (Only when current_config.nodes HAS nodes)
# ============================================================================

EDITING_INSTRUCTIONS = """
✏️ EDITING MODE - You are continuing/editing an existing workflow.

⚠️⚠️⚠️ CRITICAL: DO NOT ADD MORE TRIGGER NODES! ⚠️⚠️⚠️
The workflow ALREADY HAS NODES. You are in editing/continuation mode.

CURRENT WORKFLOW STATE:
- Existing nodes: {node_count} nodes
- Existing edges: {edge_count} edges
- Node IDs: {node_ids}
- Pending tasks: {pending_task_count} tasks

📋 TASK QUEUE MANAGEMENT (YOUR TODO SYSTEM):

BEFORE deciding what to do, CHECK pending_tasks IN THIS ORDER:

1. **Check for pending tasks**:
   - Look at ctx.deps.pending_tasks
   - Find first task with status="pending"
   - Execute that task

2. **If NO pending tasks**:
   - Analyze user message
   - Determine what needs to be done
   - Create task queue for multi-step operations

TASK TYPES & 3-STEP WORKFLOW CYCLE:

When adding a new node, you create a SEQUENCE of tasks:

Step 1: CREATE NODE (node_add)
  Task: {{"id": "task_1", "type": "create_node", "status": "in_progress", "node_type": "database", "details": {{...}}}}
  Action: Delegate to worker → Get credential_id + schema → node_add with FULL config
  After: Mark task_1 completed, create task_2

Step 2: VERIFY CONFIG (auto-check)
  Task: {{"id": "task_2", "type": "verify_config", "status": "pending", "node_id": "node_2"}}
  Action: Check if node has all required fields (from NODE_CONFIGURATION_SCHEMAS)
  After: If valid → Mark completed, create task_3; If invalid → Fix config

Step 3: CONNECT EDGE (edge_add)
  Task: {{"id": "task_3", "type": "connect_edge", "status": "pending", "source": "node_1", "target": "node_2"}}
  Action: edge_add to connect nodes
  After: Mark completed

EXAMPLE FLOW:

Turn 1: User: "I want to process call transcripts"
        pending_tasks: []
        AI: Creates task_1: {{"type": "create_node", "node_type": "trigger_manual"}}
        AI: Executes task_1 → node_add trigger
        AI: Marks task_1 completed, creates task_2: {{"type": "create_node", "node_type": "database"}}
        pending_tasks: [task_2: create database node]

Turn 2: User: "okay" (continuation)
        pending_tasks: [task_2: create database node]
        AI: Sees pending task_2
        AI: Executes task_2 → Delegates to worker → node_add database with full config
        AI: Marks task_2 completed, creates task_3: {{"type": "connect_edge", "source": "node_1", "target": "node_2"}}
        pending_tasks: [task_3: connect nodes]

Turn 3: User: "sure" (continuation)
        pending_tasks: [task_3: connect edge]
        AI: Sees pending task_3
        AI: Executes task_3 → edge_add
        AI: Marks task_3 completed, creates task_4: {{"type": "create_node", "node_type": "agent"}}
        pending_tasks: [task_4: create agent node]

CRITICAL RULES:
1. ALWAYS check pending_tasks FIRST before analyzing user message
2. When user says "okay"/"yes"/"continue" → Execute next pending task (DON'T create new tasks)
3. After node_add → ALWAYS create follow-up task for edge connection
4. NEVER ask "what next?" - check task queue instead
5. Task queue prevents you from getting "estranged" - it's your memory

RECOGNIZE CONTINUATION MESSAGES:
User says: "okay", "yes", "sure", "continue", "proceed", "go ahead", "next", "sounds good"
→ This means "proceed to the NEXT logical step in workflow building"
→ DO NOT treat as new workflow request
→ DO NOT re-analyze for trigger type
→ CHECK what exists and add the NEXT needed component

WORKFLOW BUILDING STRATEGY:

STEP 1: Analyze what exists
- Has trigger only? → Add database or first processing node
- Has trigger + database? → Connect them OR add agent
- Has unconnected nodes? → Add edges to connect them
- Has all main nodes but missing connections? → Add missing edges
- Workflow looks complete? → workflow_complete

STEP 2: Add next logical component
For each missing component:
1. Delegate to worker if needed (credentials, agents, schema)
2. Add fully configured node OR add edge
3. Wait for next user continuation

Example Continuation Flow:
Turn 1: User: "I want to process call transcripts"
        AI: Adds trigger_manual

Turn 2: User: "okay"  [CONTINUATION - not new request!]
        AI: Checks existing → Has trigger only → Needs database
        AI: Delegates to worker → Gets credentials + schema → Adds database node with FULL config

Turn 3: User: "continue"  [CONTINUATION - not new request!]
        AI: Checks existing → Has trigger + database, no edges → Needs connection
        AI: edge_add (connects trigger to database)

Turn 4: User: "sure"  [CONTINUATION - not new request!]
        AI: Checks existing → Has trigger + database + edge → Needs agent
        AI: Delegates to worker → Gets agents → Adds agent node with FULL config

Turn 5: User: "yes"  [CONTINUATION - not new request!]
        AI: Checks existing → Has agent but not connected → Needs edge
        AI: edge_add (connects database to agent)

Turn 6: User: "keep going"  [CONTINUATION - not new request!]
        AI: Checks existing → Has trigger → database → agent → Needs output
        AI: Adds output node with FULL config

Turn 7: User: "finish it"  [CONTINUATION - not new request!]
        AI: Checks existing → Has output but not connected → Needs edge
        AI: edge_add (connects agent to output)

Turn 8: User: "done"  [CONTINUATION - not new request!]
        AI: Checks existing → All nodes connected → workflow_complete

EDITING SPECIFIC NODES:
User: "Change the SQL query in the database node"
→ Use node_edit with node ID from current_config.nodes

User: "Remove the filter node"
→ Use node_remove with node ID

POSITION CALCULATION FOR NEW NODES:
- Find rightmost existing node's x coordinate
- New node x = rightmost_x + 300
- Keep y = 200 for linear flows

IMPORTANT FOR EDITING MODE:
1. NEVER add another trigger node - one already exists
2. ALWAYS check current_config.nodes before deciding next action
3. ALWAYS recognize continuation words as "proceed to next step"
4. NEVER ask "what kind of workflow?" - you're already building one!
5. Reference existing nodes by their IDs from current_config.nodes
"""

# ============================================================================
# Common Instructions (Always Present)
# ============================================================================

COMMON_INSTRUCTIONS = """
IMPORTANT RULES:
1. ONE COMPLETE ACTION PER TURN:
   - Each response = ONE WorkflowBuilderResponse (node_add OR edge_add OR conversation, etc.)
   - Can delegate to worker in same turn, but only return ONE action

2. DELEGATE BEFORE ADDING NODES:
   - Call worker to get credentials/agents/schema
   - Use results to build FULL config
   - Add node with complete config in node_add action
   - DO NOT add empty nodes then configure with node_edit later

3. node_edit is ONLY for user-requested changes, NOT initial configuration

4. POSITION IS REQUIRED: Always use the pre-calculated position from the "NEXT NODE POSITION" section, NEVER empty {}

5. Only use "conversation" when you genuinely need user input - not for confirmations

6. Be efficient - work autonomously, only speak when truly necessary

7. Do NOT include "connects_to" field in node_add - use edge_add action instead

REMEMBER:
- You are context-aware - use current_config to inform decisions
- You are autonomous - build workflows efficiently
- You are efficient - only ask when genuinely stuck
- You are structured - always return WorkflowBuilderResponse
- You are intelligent - understand user intent from context
"""

# ============================================================================
# Dynamic System Prompt (State-Dependent)
# ============================================================================

def get_supervisor_instructions(ctx: RunContext[SupervisorDeps]) -> str:
    """
    Generate dynamic system prompt based on workflow state.

    - If current_config.nodes is EMPTY → Return NEW WORKFLOW prompt (with trigger detection)
    - If current_config.nodes HAS nodes → Return EDITING prompt (NO trigger detection)
    """
    node_count = len(ctx.deps.current_config.nodes)
    edge_count = len(ctx.deps.current_config.edges)

    # Calculate next node position using the helper method
    next_position = ctx.deps.get_next_node_position()
    position_str = f'{{"x": {next_position["x"]}, "y": {next_position["y"]}}}'

    # Always start with node configuration schemas (critical reference material)
    prompt = NODE_CONFIGURATION_SCHEMAS + "\n\n"

    # Then base instructions
    prompt += BASE_INSTRUCTIONS + "\n\n"

    # Add calculated position instruction
    prompt += f"""
🎯 NEXT NODE POSITION (PRE-CALCULATED):
Use this EXACT position for any new node you add: {position_str}

CRITICAL: Copy this position value exactly into your node_add response.
DO NOT calculate position yourself - use the value provided above.

"""

    if node_count == 0:
        # NEW WORKFLOW MODE - Include trigger detection
        prompt += NEW_WORKFLOW_INSTRUCTIONS
    else:
        # EDITING MODE - NO trigger detection, focus on continuation
        node_ids = [str(node.get('id', 'unknown')) for node in ctx.deps.current_config.nodes]
        pending_task_count = len([t for t in ctx.deps.pending_tasks if t.get('status') == 'pending'])
        editing_prompt = EDITING_INSTRUCTIONS.format(
            node_count=node_count,
            edge_count=edge_count,
            node_ids=", ".join(node_ids),
            pending_task_count=pending_task_count
        )
        prompt += editing_prompt

    # Always end with common instructions
    prompt += "\n\n" + COMMON_INSTRUCTIONS

    return prompt

# Create supervisor agent with dynamic instructions
supervisor_agent = Agent(
    model,
    deps_type=SupervisorDeps,
    output_type=WorkflowBuilderResponse,
    instructions=get_supervisor_instructions,  # Dynamic function, not static string!
)

print(f"\n{'*'*80}")
print(f"👔 SUPERVISOR AGENT INITIALIZED (Dynamic Prompts)")
print(f"   Model: {MODEL_NAME}")
print(f"   Tool: delegate_to_worker")
print(f"   Output: Structured (WorkflowBuilderResponse)")
print(f"   Prompt Mode: DYNAMIC (state-dependent)")
print(f"{'*'*80}\n")


# ============================================================================
# Output Validator - Enforce Complete Configurations
# ============================================================================

@supervisor_agent.output_validator
def validate_node_config(ctx: RunContext[SupervisorDeps], response: WorkflowBuilderResponse) -> WorkflowBuilderResponse:
    """
    Validate that actions have complete, valid data.

    Raises ModelRetry if validation fails - this forces the agent to try again.
    """

    # Validate node_add - must have complete config
    if response.action_type == "node_add":
        node_type = response.data.node_type
        config = response.data.config or {}

        # Check position is valid (Position is a Pydantic model, so x and y are guaranteed by schema)
        # This validation is now redundant since Pydantic enforces x and y as required fields,
        # but we keep it for explicit error messages if somehow validation is bypassed
        if not response.data.position:
            raise ModelRetry(
                f"node_add requires valid position with x and y coordinates. Got: {response.data.position}\n\n"
                f"REQUIRED FORMAT: {{\"x\": <number>, \"y\": <number>}}\n\n"
                f"FIX: Look at the 'NEXT NODE POSITION (PRE-CALCULATED)' section in your instructions.\n"
                f"Copy that EXACT position value into your node_add response.\n\n"
                f"DO NOT calculate position yourself - use the pre-calculated value from the instructions.\n\n"
                f"Try again with the correct position from the instructions."
            )

        # Validate required fields based on node type
        if node_type == "database":
            if not config.get("credential_id"):
                raise ModelRetry(
                    f"database node requires credential_id in config.\n\n"
                    f"If you just delegated to worker to inspect a credential's schema, include that credential_id in the config.\n"
                    f"Example: If you inspected credential 3, use: config = {{\"credential_id\": 3, \"query\": \"...\"}}\n\n"
                    f"If you haven't gotten credentials yet, delegate to worker with get_credentials tool first."
                )
            if not config.get("query"):
                raise ModelRetry(
                    f"database node requires query in config.\n\n"
                    f"Generate the SQL query using the schema information from inspect_database_schema.\n"
                    f"The query must use actual table and column names from the schema.\n\n"
                    f"If you haven't inspected the schema yet, delegate to worker with inspect_database_schema tool first."
                )

        elif node_type == "agent":
            if not config.get("agent_id"):
                raise ModelRetry(
                    "agent node requires agent_id - delegate to worker with get_agents tool to get it"
                )
            if not config.get("llm_credential_id"):
                raise ModelRetry(
                    "agent node requires llm_credential_id - delegate to worker with get_credentials tool to get it"
                )

        elif node_type == "trigger_schedule":
            if not config.get("schedule"):
                raise ModelRetry(
                    "trigger_schedule node requires schedule (cron expression) - parse from user request"
                )

        elif node_type == "trigger_chat":
            if not config.get("welcome_message"):
                raise ModelRetry(
                    "trigger_chat node requires welcome_message - generate a friendly greeting"
                )

        elif node_type == "output":
            if not config.get("output_type"):
                raise ModelRetry(
                    "output node requires output_type ('database', 'file', or 'api')"
                )

            output_type = config.get("output_type")
            if output_type == "database":
                if not config.get("credential_id"):
                    raise ModelRetry(
                        "output node with output_type='database' requires credential_id"
                    )
                if not config.get("table_name"):
                    raise ModelRetry(
                        "output node with output_type='database' requires table_name"
                    )
            elif output_type == "file":
                if not config.get("file_path"):
                    raise ModelRetry(
                        "output node with output_type='file' requires file_path"
                    )
                if not config.get("file_format"):
                    raise ModelRetry(
                        "output node with output_type='file' requires file_format ('csv' or 'json')"
                    )

        elif node_type == "filter":
            if not config.get("conditions"):
                raise ModelRetry(
                    "filter node requires conditions array with at least one condition"
                )
            if not config.get("operator"):
                raise ModelRetry(
                    "filter node requires operator ('AND' or 'OR')"
                )

        elif node_type == "script":
            if not config.get("language"):
                raise ModelRetry(
                    "script node requires language ('python' or 'javascript')"
                )
            if not config.get("script"):
                raise ModelRetry(
                    "script node requires script (the actual code to execute)"
                )

        elif node_type == "conditional":
            if not config.get("condition"):
                raise ModelRetry(
                    "conditional node requires condition (JavaScript expression)"
                )
            if not config.get("condition_type"):
                raise ModelRetry(
                    "conditional node requires condition_type ('expression', 'field_value', or 'record_count')"
                )

    # Validate node_edit - must have non-empty config_updates
    elif response.action_type == "node_edit":
        if not response.data.config_updates:
            raise ModelRetry(
                f"node_edit requires config_updates with fields to change. Got empty config_updates. "
                f"If you want to add a node, use node_add instead."
            )

        # Verify node exists
        node_id = response.data.node_id
        node = ctx.deps.get_node_by_id(node_id)
        if not node:
            raise ModelRetry(
                f"node_edit failed: node_id '{node_id}' does not exist. Available nodes: {[n.get('id') for n in ctx.deps.current_config.nodes]}"
            )

    # Validate edge_add - verify nodes exist
    elif response.action_type == "edge_add":
        source = response.data.source
        target = response.data.target

        source_node = ctx.deps.get_node_by_id(source)
        target_node = ctx.deps.get_node_by_id(target)

        if not source_node:
            raise ModelRetry(
                f"edge_add failed: source node '{source}' does not exist. Available nodes: {[n.get('id') for n in ctx.deps.current_config.nodes]}"
            )
        if not target_node:
            raise ModelRetry(
                f"edge_add failed: target node '{target}' does not exist. Available nodes: {[n.get('id') for n in ctx.deps.current_config.nodes]}"
            )

    # Validation passed
    return response


# ============================================================================
# Supervisor Agent Tool: Delegation
# ============================================================================

@supervisor_agent.tool
async def delegate_to_worker(
    ctx: RunContext[SupervisorDeps],
    task_description: str,
    required_tools: Annotated[
        list[str],
        "List of tool names needed: get_credentials, get_agents, inspect_database_schema, query_database"
    ]
) -> WorkerToolResult:
    """
    Delegate tool execution to worker agent.

    Worker executes tools autonomously and returns results.

    Args:
        task_description: Description of what the worker should do
        required_tools: List of tool names that worker may need to use

    Returns:
        WorkerToolResult with execution results

    Example:
        task = "Find all database credentials for the user"
        tools = ["get_credentials"]
        result = await delegate_to_worker(ctx, task, tools)
    """
    session_id = ctx.deps.session_id

    print(f"\n{'='*80}")
    print(f"👔 SUPERVISOR: Delegating to worker")
    print(f"   Task: {task_description}")
    print(f"   Required Tools: {', '.join(required_tools)}")
    print(f"{'='*80}\n")

    # Create worker prompt
    worker_prompt = f"""
Execute this task: {task_description}

You have these tools available: {', '.join(required_tools)}

Execute the necessary tools and report back with complete results.
"""

    # Run worker agent
    worker_deps = WorkerDeps(session_id=session_id)

    try:
        result = await worker_agent.run(worker_prompt, deps=worker_deps)

        print(f"✅ SUPERVISOR: Worker completed task")
        print(f"   Result: {result.output.summary}")

        return result.output

    except Exception as e:
        error_msg = f"Worker execution failed: {str(e)}"
        print(f"❌ SUPERVISOR: {error_msg}")

        return WorkerToolResult(
            success=False,
            tool_name="delegate_to_worker",
            result={},
            summary="Delegation failed",
            error=error_msg
        )
