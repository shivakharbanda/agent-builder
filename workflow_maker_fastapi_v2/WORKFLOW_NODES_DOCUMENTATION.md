# Workflow Nodes Documentation

**Version:** 2.0
**Last Updated:** 2025-10-17
**Purpose:** Complete reference for workflow node types, configurations, and frontend integration

This document provides comprehensive specifications for all workflow node types supported by the Agent Builder platform, including trigger nodes, data nodes, processing nodes, and output nodes.

---

## Table of Contents

### [Trigger Nodes (Start Nodes)](#trigger-nodes-start-nodes-1)
1. [Manual Trigger](#1-manual-trigger-trigger_manual)
2. [Schedule Trigger](#2-schedule-trigger-trigger_schedule)
3. [Chat Trigger](#3-chat-trigger-trigger_chat)

### [Data Source Nodes](#data-source-nodes-1)
4. [Database Node](#4-database-node-database)

### [Processing Nodes](#processing-nodes-1)
5. [Agent Node](#5-agent-node-agent)
6. [Toolbox Node](#6-toolbox-node-toolbox)
7. [Filter Node](#7-filter-node-filter)
8. [Script Node](#8-script-node-script)
9. [Conditional Node](#9-conditional-node-conditional)

### [Output Nodes](#output-nodes-1)
10. [Output Node](#10-output-node-output)

### [Appendices](#appendices-1)
- [Frontend Field Types Reference](#frontend-field-types-reference)
- [Conditional Field Visibility](#conditional-field-visibility)
- [Validation Rules](#validation-rules)
- [Node Connection Rules](#node-connection-rules)

---

# Trigger Nodes (Start Nodes)

Trigger nodes are the entry points for workflows. They determine when and how a workflow execution begins. **Every workflow must have exactly ONE trigger node.**

---

## 1. Manual Trigger (`trigger_manual`)

### Overview

| Property | Value |
|----------|-------|
| **Node Type** | `trigger_manual` |
| **Name** | Manual Trigger |
| **Description** | Start workflow manually via button click or API call |
| **Icon** | `play_circle` (Material Icons) |
| **Category** | `trigger` |
| **Use Case** | On-demand workflow execution |

### Frontend Expected Structure

```json
{
  "id": "trigger-1",
  "type": "trigger_manual",
  "position": {"x": 100, "y": 200},
  "config": {
    "description": "string (optional)",
    "initial_data": "json string (optional)"
  }
}
```

### Configuration Fields

| Field Name | Type | Required | Default | Validation |
|------------|------|----------|---------|------------|
| `description` | `textarea` | ❌ No | - | - |
| `initial_data` | `code_editor` | ❌ No | - | Must be valid JSON |

#### Field Details

**description:**
- **Label:** "Description"
- **Placeholder:** "Describe when to run this workflow manually..."
- **Rows:** 2
- **Help:** "Human-readable description of when to trigger this workflow"
- **Frontend Component:** Textarea

**initial_data:**
- **Label:** "Initial Data (JSON)"
- **Placeholder:** `{"key": "value"}`
- **Rows:** 6
- **Help:** "Optional JSON data to pass to downstream nodes"
- **Frontend Component:** Code editor (monospace textarea)
- **Validation:** Must be valid JSON if provided

### Outputs

| Output Name | Type | Description |
|-------------|------|-------------|
| `data` | `any` | Initial data or execution metadata |

### Example Configuration

```json
{
  "type": "trigger_manual",
  "config": {
    "description": "Process customer data on demand",
    "initial_data": "{\"source\": \"manual_trigger\", \"timestamp\": \"2024-01-01T00:00:00Z\"}"
  }
}
```

### Backend Execution

- Workflow starts when user clicks "Run" button or API call made
- `initial_data` (if provided) is passed to first connected node
- If no `initial_data`, passes execution metadata (execution_id, timestamp, etc.)
- Always returns success immediately

---

## 2. Schedule Trigger (`trigger_schedule`)

### Overview

| Property | Value |
|----------|-------|
| **Node Type** | `trigger_schedule` |
| **Name** | Schedule Trigger |
| **Description** | Run workflow on a recurring schedule |
| **Icon** | `schedule` (Material Icons) |
| **Category** | `trigger` |
| **Use Case** | Automated recurring execution (daily reports, hourly sync, etc.) |

### Frontend Expected Structure

```json
{
  "id": "trigger-1",
  "type": "trigger_schedule",
  "position": {"x": 100, "y": 200},
  "config": {
    "schedule": "0 9 * * *",
    "timezone": "UTC",
    "enabled": true,
    "description": "string (optional)"
  }
}
```

### Configuration Fields

| Field Name | Type | Required | Default | Validation |
|------------|------|----------|---------|------------|
| `description` | `textarea` | ❌ No | - | - |
| `schedule` | `text` | ✅ Yes | - | Valid cron expression |
| `timezone` | `select` | ❌ No | `"UTC"` | Must be valid timezone |
| `enabled` | `checkbox` | ❌ No | `true` | Boolean |

#### Field Details

**description:**
- **Label:** "Description"
- **Placeholder:** "Describe this scheduled workflow..."
- **Rows:** 2
- **Help:** "Human-readable description of the schedule"
- **Frontend Component:** Textarea

**schedule:**
- **Label:** "Cron Expression"
- **Placeholder:** "0 9 * * * (Daily at 9am)"
- **Help:** "Cron syntax: minute hour day month weekday. Examples: '0 9 * * *' (9am daily), '*/15 * * * *' (every 15 min)"
- **Frontend Component:** Text input
- **Validation:** Must be valid cron expression (5 or 6 parts)
- **Format:** `[minute] [hour] [day-of-month] [month] [day-of-week]`

**Common Cron Examples:**
- `0 9 * * *` - Daily at 9:00 AM
- `*/15 * * * *` - Every 15 minutes
- `0 * * * *` - Every hour
- `0 0 * * 0` - Weekly on Sunday at midnight
- `0 0 1 * *` - Monthly on the 1st at midnight

**timezone:**
- **Label:** "Timezone"
- **Placeholder:** "Select timezone"
- **Default:** "UTC"
- **Help:** "Timezone for schedule execution"
- **Frontend Component:** Select dropdown
- **Options:**
  - `UTC` - UTC
  - `America/New_York` - Eastern Time (US)
  - `America/Chicago` - Central Time (US)
  - `America/Denver` - Mountain Time (US)
  - `America/Los_Angeles` - Pacific Time (US)
  - `Europe/London` - London (GMT/BST)
  - `Europe/Paris` - Paris (CET/CEST)
  - `Asia/Tokyo` - Tokyo (JST)
  - `Asia/Shanghai` - Shanghai (CST)
  - `Australia/Sydney` - Sydney (AEST/AEDT)

**enabled:**
- **Label:** "Enable Schedule"
- **Default:** `true`
- **Help:** "Toggle to enable/disable scheduled execution"
- **Frontend Component:** Checkbox

### Outputs

| Output Name | Type | Description |
|-------------|------|-------------|
| `data` | `any` | Execution metadata with schedule info |

### Example Configuration

```json
{
  "type": "trigger_schedule",
  "config": {
    "description": "Daily customer report at 9 AM Eastern",
    "schedule": "0 9 * * *",
    "timezone": "America/New_York",
    "enabled": true
  }
}
```

### Backend Execution

- Scheduler checks cron expression against current time in specified timezone
- When time matches, workflow execution starts automatically
- `enabled` flag controls whether schedule is active
- Passes execution metadata (scheduled_time, actual_time, execution_id) to downstream nodes
- Schedule runs even if previous execution still running (unless configured otherwise at workflow level)

---

## 3. Chat Trigger (`trigger_chat`)

### Overview

| Property | Value |
|----------|-------|
| **Node Type** | `trigger_chat` |
| **Name** | Chat Trigger |
| **Description** | Start workflow from user chat messages |
| **Icon** | `chat` (Material Icons) |
| **Category** | `trigger` |
| **Use Case** | Interactive chatbot workflows, conversational interfaces |

### Frontend Expected Structure

```json
{
  "id": "trigger-1",
  "type": "trigger_chat",
  "position": {"x": 100, "y": 200},
  "config": {
    "welcome_message": "Hi! How can I help you?",
    "context_instructions": "string (optional)",
    "description": "string (optional)"
  }
}
```

### Configuration Fields

| Field Name | Type | Required | Default | Validation |
|------------|------|----------|---------|------------|
| `welcome_message` | `textarea` | ✅ Yes | - | Non-empty string |
| `context_instructions` | `textarea` | ❌ No | - | - |
| `description` | `textarea` | ❌ No | - | - |

#### Field Details

**welcome_message:**
- **Label:** "Welcome Message"
- **Placeholder:** "Hi! Send me a message to start the workflow..."
- **Rows:** 3
- **Help:** "Initial message shown to users when they open the chat"
- **Frontend Component:** Textarea
- **Required:** Yes

**context_instructions:**
- **Label:** "Processing Instructions"
- **Placeholder:** "How to interpret and process user input..."
- **Rows:** 4
- **Help:** "Instructions for how downstream nodes should process the chat input"
- **Frontend Component:** Textarea

**description:**
- **Label:** "Description"
- **Placeholder:** "Describe this chat-triggered workflow..."
- **Rows:** 2
- **Help:** "Human-readable description of the workflow"
- **Frontend Component:** Textarea

### Outputs

| Output Name | Type | Description |
|-------------|------|-------------|
| `user_input` | `string` | User's chat message |
| `session_id` | `string` | Chat session identifier for conversation continuity |
| `parsed_data` | `object` | Structured data extracted from message (if applicable) |

### Example Configuration

```json
{
  "type": "trigger_chat",
  "config": {
    "welcome_message": "Hi! I'm your data assistant. Ask me anything about your customer data.",
    "context_instructions": "Extract customer name, email, and question from user message. Pass to agent for processing.",
    "description": "Customer support chatbot workflow"
  }
}
```

### Backend Execution

- Chat interface displays `welcome_message` when user opens chat
- When user sends message, workflow execution starts
- User's message is passed as `user_input` to connected nodes
- `session_id` maintains conversation context across multiple messages
- Workflow can return response via output node, which appears in chat as bot message
- Special handling: Output nodes with chat response are displayed in chat UI

---

# Data Source Nodes

Data source nodes fetch data from external sources (databases, APIs, files).

---

## 4. Database Node (`database`)

### Overview

| Property | Value |
|----------|-------|
| **Node Type** | `database` |
| **Name** | Database |
| **Description** | Connects to your database to read data |
| **Icon** | `storage` (Material Icons) |
| **Category** | `data_source` |
| **Use Case** | Fetch data from SQL databases using custom queries |

### Frontend Expected Structure

```json
{
  "id": "node-1",
  "type": "database",
  "position": {"x": 400, "y": 200},
  "config": {
    "credential_id": 5,
    "query": "SELECT * FROM customers WHERE status = {{status}}",
    "placeholders": {
      "status": "active"
    }
  }
}
```

### Configuration Fields

| Field Name | Type | Required | Default | Validation |
|------------|------|----------|---------|------------|
| `credential_id` | `credential_select` | ✅ Yes | - | Valid RDBMS credential |
| `query` | `textarea` | ✅ Yes | - | Non-empty SQL query |
| `placeholders` | `placeholder_mapping` | ❌ No | - | - |

#### Field Details

**credential_id:**
- **Label:** "Database Connection"
- **Placeholder:** "Select a database credential"
- **Help:** "Choose the database connection to use for this node"
- **Frontend Component:** Credential selector dropdown
- **Category Filter:** `RDBMS` (filters to only show database credentials)
- **API Endpoint:** `/api/credentials/credentials/?category=RDBMS`
- **Display Format:** Shows credential name and database type

**query:**
- **Label:** "SQL Query"
- **Placeholder:** `SELECT * FROM table WHERE column = {{placeholder}}`
- **Rows:** 6
- **Help:** "Write your SQL query. Use {{placeholder}} for dynamic values that will be replaced at runtime"
- **Frontend Component:** Textarea (monospace font recommended)
- **Supports:** Dynamic placeholders using `{{placeholder_name}}` syntax

**placeholders:**
- **Label:** "Dynamic Placeholders"
- **Placeholder:** "Map placeholder values"
- **Help:** "Define the values for placeholders used in your query"
- **Frontend Component:** Custom placeholder mapping component
- **Format:** Key-value pairs where key matches `{{placeholder}}` in query
- **Example:** `{"status": "active", "start_date": "2024-01-01"}`

### Outputs

| Output Name | Type | Description |
|-------------|------|-------------|
| `data` | `table` | Query results as array of row objects |

### Example Configuration

```json
{
  "type": "database",
  "config": {
    "credential_id": 5,
    "query": "SELECT customer_id, name, email, order_date FROM orders WHERE order_date > {{start_date}} AND status = {{status}} LIMIT {{limit}}",
    "placeholders": {
      "start_date": "2024-01-01",
      "status": "completed",
      "limit": "1000"
    }
  }
}
```

### Backend Execution

- Connects to database using `credential_id`
- Replaces all `{{placeholder}}` tokens with values from `placeholders` config
- Executes SQL query
- Returns results as array of objects (one object per row)
- Column names become object keys
- Handles NULL values appropriately
- Query timeout configurable at workflow level
- Connection pooling recommended for performance

**Example Output:**
```json
{
  "data": [
    {"customer_id": 1, "name": "John Doe", "email": "john@example.com", "order_date": "2024-01-15"},
    {"customer_id": 2, "name": "Jane Smith", "email": "jane@example.com", "order_date": "2024-01-20"}
  ]
}
```

---

# Processing Nodes

Processing nodes transform, filter, or analyze data flowing through the workflow.

---

## 5. Agent Node (`agent`)

### Overview

| Property | Value |
|----------|-------|
| **Node Type** | `agent` |
| **Name** | AI Agent |
| **Description** | Process data using an AI agent |
| **Icon** | `smart_toy` (Material Icons) |
| **Category** | `processor` |
| **Use Case** | AI/ML processing (classification, extraction, summarization, etc.) |

### Frontend Expected Structure

```json
{
  "id": "node-2",
  "type": "agent",
  "position": {"x": 700, "y": 200},
  "config": {
    "agent_id": 12,
    "llm_credential_id": 3,
    "model": "gemini-1.5-flash",
    "input_mapping": {
      "customer_name": "name",
      "customer_email": "email"
    },
    "batch_size": 100,
    "timeout": 30
  }
}
```

### Configuration Fields

| Field Name | Type | Required | Default | Validation |
|------------|------|----------|---------|------------|
| `agent_id` | `agent_select` | ✅ Yes | - | Valid agent ID |
| `llm_credential_id` | `credential_select` | ✅ Yes | - | Valid LLM credential |
| `model` | `text` | ❌ No | From credential | Valid model name |
| `input_mapping` | `input_mapping` | ❌ No | - | - |
| `batch_size` | `number` | ❌ No | `100` | 1-1000 |
| `timeout` | `number` | ❌ No | `30` | 5-300 seconds |

#### Field Details

**agent_id:**
- **Label:** "AI Agent"
- **Placeholder:** "Select an AI agent"
- **Help:** "Choose which AI agent will process the input data"
- **Frontend Component:** Agent selector dropdown
- **API Endpoint:** `/api/agents/`
- **Display Format:** Shows agent name, description, and return type

**llm_credential_id:**
- **Label:** "LLM Connection"
- **Placeholder:** "Select an LLM credential"
- **Help:** "Choose the LLM provider (OpenAI, Gemini, etc.) for agent execution"
- **Frontend Component:** Credential selector dropdown
- **Category Filter:** `LLM`
- **API Endpoint:** `/api/credentials/credentials/?category=LLM`

**model:**
- **Label:** "Model Name"
- **Placeholder:** "e.g., gemini-1.5-flash, gpt-4o"
- **Help:** "Specific model to use (optional, defaults to credential's model)"
- **Frontend Component:** Text input
- **Examples:** `gemini-1.5-flash`, `gpt-4o`, `claude-3-opus`

**input_mapping:**
- **Label:** "Input Data Mapping"
- **Placeholder:** "Map input fields to agent inputs"
- **Help:** "Define how input data should be mapped to the agent's expected inputs"
- **Frontend Component:** Custom input mapping component
- **Purpose:** Maps incoming data fields to agent prompt placeholders
- **Format:** Object with keys = agent prompt placeholders, values = input field names

**batch_size:**
- **Label:** "Batch Size"
- **Placeholder:** "100"
- **Min:** 1
- **Max:** 1000
- **Default:** 100
- **Help:** "Number of records to process at once"
- **Frontend Component:** Number input

**timeout:**
- **Label:** "Timeout (seconds)"
- **Placeholder:** "30"
- **Min:** 5
- **Max:** 300
- **Default:** 30
- **Help:** "Maximum time to wait for agent response"
- **Frontend Component:** Number input

### Inputs

| Input Name | Type | Description |
|------------|------|-------------|
| `data` | `any` | Input data to be processed (typically array of objects) |

### Outputs

| Output Name | Type | Description |
|-------------|------|-------------|
| `result` | `any` | Processed data from the agent (structure depends on agent return type) |

### Example Configuration

```json
{
  "type": "agent",
  "config": {
    "agent_id": 12,
    "llm_credential_id": 3,
    "model": "gemini-1.5-flash",
    "input_mapping": {
      "customer_name": "name",
      "customer_email": "email",
      "order_details": "order_text"
    },
    "batch_size": 50,
    "timeout": 60
  }
}
```

### Backend Execution

- Fetches agent configuration by `agent_id`
- Connects to LLM using `llm_credential_id`
- Input data is batched according to `batch_size`
- For each batch:
  - Maps input fields using `input_mapping`
  - Fills agent prompt placeholders
  - Calls LLM with timeout
  - Parses response based on agent return type
- Returns aggregated results
- Timeout applies per batch, not total execution
- Failed batches can retry based on workflow config

**Example Output (if agent returns structured data):**
```json
{
  "result": [
    {"customer_id": 1, "sentiment": "positive", "intent": "purchase"},
    {"customer_id": 2, "sentiment": "negative", "intent": "complaint"}
  ]
}
```

---

## 6. Toolbox Node (`toolbox`)

### Overview

| Property | Value |
|----------|-------|
| **Node Type** | `toolbox` |
| **Name** | Toolbox |
| **Description** | Attach tools to AI agents |
| **Icon** | `construction` (Material Icons) |
| **Category** | `tools` |
| **Use Case** | Provide MCP servers or internal tools to agent nodes |

### Frontend Expected Structure

```json
{
  "id": "toolbox-1",
  "type": "toolbox",
  "position": {"x": 550, "y": 200},
  "config": {
    "mcp_server_ids": [1, 2, 5],
    "internal_tool_attachments": [
      {"tool_id": 3, "credential_id": 7},
      {"tool_id": 8, "credential_id": 9}
    ]
  }
}
```

### Configuration Fields

| Field Name | Type | Required | Default | Validation |
|------------|------|----------|---------|------------|
| `mcp_server_ids` | `mcp_server_multi_select` | ❌ No | `[]` | Array of valid MCP server IDs |
| `internal_tool_attachments` | `internal_tool_multi_select` | ❌ No | `[]` | Array of tool+credential pairs |

#### Field Details

**mcp_server_ids:**
- **Label:** "MCP Servers"
- **Placeholder:** "Select MCP servers"
- **Help:** "Select MCP servers to provide to the connected agent"
- **Frontend Component:** Multi-select dropdown
- **API Endpoint:** `/api/mcp-servers/` (or similar)
- **Format:** Array of MCP server IDs
- **Purpose:** Provides external tools via MCP protocol

**internal_tool_attachments:**
- **Label:** "Internal Tools"
- **Placeholder:** "Select internal tools with credentials"
- **Help:** "Select internal tools and their credentials for the agent"
- **Frontend Component:** Custom multi-select with credential pairing
- **Format:** Array of objects with `tool_id` and `credential_id`
- **Purpose:** Attaches internal tools (database query, API call, etc.) with authentication

### Outputs

| Output Name | Type | Description |
|-------------|------|-------------|
| `tools_config` | `config` | Tool configuration provided to connected agent node |

### Example Configuration

```json
{
  "type": "toolbox",
  "config": {
    "mcp_server_ids": [1, 2],
    "internal_tool_attachments": [
      {"tool_id": 3, "credential_id": 5},
      {"tool_id": 7, "credential_id": 5}
    ]
  }
}
```

### Backend Execution

- Toolbox node connects BETWEEN a data source and an agent node
- Fetches tool definitions from MCP servers
- Attaches internal tools with credentials
- Passes tool configuration to connected agent node
- Agent can then call these tools during execution
- Tools are scoped to the agent's execution context

**Connection Pattern:**
```
Database → Toolbox → Agent → Output
          (provides tools to agent)
```

---

## 7. Filter Node (`filter`)

### Overview

| Property | Value |
|----------|-------|
| **Node Type** | `filter` |
| **Name** | Filter |
| **Description** | Filter and select data based on conditions |
| **Icon** | `filter_alt` (Material Icons) |
| **Category** | `processor` |
| **Use Case** | Filter rows based on conditional logic |

### Frontend Expected Structure

```json
{
  "id": "filter-1",
  "type": "filter",
  "position": {"x": 550, "y": 200},
  "config": {
    "conditions": [
      {"field": "age", "operator": ">", "value": 18},
      {"field": "status", "operator": "==", "value": "active"}
    ],
    "operator": "AND"
  }
}
```

### Configuration Fields

| Field Name | Type | Required | Default | Validation |
|------------|------|----------|---------|------------|
| `conditions` | `filter_conditions` | ✅ Yes | - | At least one condition |
| `operator` | `select` | ✅ Yes | `"AND"` | Must be AND or OR |

#### Field Details

**conditions:**
- **Label:** "Filter Conditions"
- **Placeholder:** "Add filter conditions"
- **Help:** "Define conditions to filter the data"
- **Frontend Component:** Custom filter conditions builder
- **Format:** Array of condition objects
- **Condition Structure:**
  ```json
  {
    "field": "field_name",
    "operator": "==|!=|>|<|>=|<=|contains|startswith|endswith",
    "value": "comparison_value"
  }
  ```

**operator:**
- **Label:** "Condition Operator"
- **Placeholder:** "AND"
- **Default:** "AND"
- **Help:** "How to combine multiple conditions"
- **Frontend Component:** Select dropdown
- **Options:**
  - `AND` - AND (all conditions must match)
  - `OR` - OR (any condition can match)

### Inputs

| Input Name | Type | Description |
|------------|------|-------------|
| `data` | `table` | Input data as array of objects |

### Outputs

| Output Name | Type | Description |
|-------------|------|-------------|
| `data` | `table` | Filtered subset of input data |

### Example Configuration

```json
{
  "type": "filter",
  "config": {
    "conditions": [
      {"field": "age", "operator": ">", "value": 18},
      {"field": "status", "operator": "==", "value": "active"},
      {"field": "email", "operator": "contains", "value": "@company.com"}
    ],
    "operator": "AND"
  }
}
```

### Supported Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `==` | Equals | `age == 25` |
| `!=` | Not equals | `status != "deleted"` |
| `>` | Greater than | `age > 18` |
| `<` | Less than | `price < 100` |
| `>=` | Greater than or equal | `score >= 70` |
| `<=` | Less than or equal | `quantity <= 10` |
| `contains` | String contains | `email contains "@gmail"` |
| `startswith` | String starts with | `name startswith "John"` |
| `endswith` | String ends with | `file endswith ".pdf"` |

### Backend Execution

- Evaluates each row against all conditions
- AND operator: row passes if ALL conditions true
- OR operator: row passes if ANY condition true
- Returns filtered array
- Empty array if no rows match
- Preserves original row structure

**Example:**
```
Input: [
  {id: 1, age: 25, status: "active"},
  {id: 2, age: 17, status: "active"},
  {id: 3, age: 30, status: "inactive"}
]

Filter: age > 18 AND status == "active"

Output: [
  {id: 1, age: 25, status: "active"}
]
```

---

## 8. Script Node (`script`)

### Overview

| Property | Value |
|----------|-------|
| **Node Type** | `script` |
| **Name** | Custom Script |
| **Description** | Run custom Python or JavaScript code |
| **Icon** | `code` (Material Icons) |
| **Category** | `processor` |
| **Use Case** | Custom data transformation or business logic |

### Frontend Expected Structure

```json
{
  "id": "script-1",
  "type": "script",
  "position": {"x": 700, "y": 200},
  "config": {
    "language": "python",
    "script": "def process(data):\\n    return [row for row in data if row['amount'] > 100]",
    "timeout": 30
  }
}
```

### Configuration Fields

| Field Name | Type | Required | Default | Validation |
|------------|------|----------|---------|------------|
| `language` | `select` | ✅ Yes | `"python"` | Must be python or javascript |
| `script` | `code_editor` | ✅ Yes | - | Non-empty string |
| `timeout` | `number` | ❌ No | `30` | 5-300 seconds |

#### Field Details

**language:**
- **Label:** "Language"
- **Placeholder:** "Select language"
- **Default:** "python"
- **Help:** "Programming language for the script"
- **Frontend Component:** Select dropdown
- **Options:**
  - `python` - Python
  - `javascript` - JavaScript

**script:**
- **Label:** "Script Code"
- **Placeholder:**
  ```python
  # Python code here
  def process(data):
      # Process your data
      return data
  ```
- **Rows:** 10
- **Help:** "Your custom code. Input data is available as 'data' variable"
- **Frontend Component:** Code editor (monospace textarea with syntax highlighting)

**timeout:**
- **Label:** "Timeout (seconds)"
- **Placeholder:** "30"
- **Min:** 5
- **Max:** 300
- **Default:** 30
- **Help:** "Maximum execution time for the script"
- **Frontend Component:** Number input

### Inputs

| Input Name | Type | Description |
|------------|------|-------------|
| `data` | `any` | Input data for the script |

### Outputs

| Output Name | Type | Description |
|-------------|------|-------------|
| `result` | `any` | Script execution result |

### Example Configurations

#### Python Example

```json
{
  "type": "script",
  "config": {
    "language": "python",
    "script": "def process(data):\n    # Add calculated field\n    for row in data:\n        row['total_value'] = row['quantity'] * row['price']\n    return data",
    "timeout": 60
  }
}
```

#### JavaScript Example

```json
{
  "type": "script",
  "config": {
    "language": "javascript",
    "script": "function process(data) {\n    return data\n        .filter(row => row.status === 'active')\n        .map(row => ({\n            ...row,\n            fullName: `${row.firstName} ${row.lastName}`\n        }));\n}",
    "timeout": 30
  }
}
```

### Backend Execution

**Python:**
- Python 3.x runtime
- Script must define `process(data)` function
- Limited standard library (security sandbox)
- No file system or network access
- Input passed as function argument
- Must return data (not modify in place)

**JavaScript:**
- Node.js runtime
- Script must define `process(data)` function
- Limited standard library
- No file system or network access
- Input passed as function argument
- Must return data

**Execution:**
- Script runs in isolated sandbox
- Timeout enforces max execution time
- Errors caught and logged
- Memory limits apply

---

## 9. Conditional Node (`conditional`)

### Overview

| Property | Value |
|----------|-------|
| **Node Type** | `conditional` |
| **Name** | Conditional |
| **Description** | Branch workflow based on conditions |
| **Icon** | `fork_right` (Material Icons) |
| **Category** | `control_flow` |
| **Use Case** | Split execution into different paths based on conditions |

### Frontend Expected Structure

```json
{
  "id": "conditional-1",
  "type": "conditional",
  "position": {"x": 850, "y": 200},
  "config": {
    "condition": "data.length > 100",
    "condition_type": "expression"
  }
}
```

### Configuration Fields

| Field Name | Type | Required | Default | Validation |
|------------|------|----------|---------|------------|
| `condition` | `text` | ✅ Yes | - | Non-empty string |
| `condition_type` | `select` | ✅ Yes | `"expression"` | Must be valid type |

#### Field Details

**condition:**
- **Label:** "Condition Expression"
- **Placeholder:** "data.length > 0"
- **Help:** "JavaScript expression that evaluates to true/false"
- **Frontend Component:** Text input
- **Has Access To:** `data` variable

**condition_type:**
- **Label:** "Condition Type"
- **Placeholder:** "Select type"
- **Default:** "expression"
- **Help:** "Type of condition to evaluate"
- **Frontend Component:** Select dropdown
- **Options:**
  - `expression` - JavaScript Expression
  - `field_value` - Field Value Comparison
  - `record_count` - Record Count Check

### Inputs

| Input Name | Type | Description |
|------------|------|-------------|
| `data` | `any` | Input data to evaluate condition against |

### Outputs

| Output Name | Type | Description |
|-------------|------|-------------|
| `true` | `any` | Output when condition evaluates to true |
| `false` | `any` | Output when condition evaluates to false |

### Example Configurations

#### Expression Type

```json
{
  "type": "conditional",
  "config": {
    "condition": "data.length > 100",
    "condition_type": "expression"
  }
}
```

#### Field Value Comparison

```json
{
  "type": "conditional",
  "config": {
    "condition": "data.status === 'approved'",
    "condition_type": "field_value"
  }
}
```

#### Record Count Check

```json
{
  "type": "conditional",
  "config": {
    "condition": "data.length >= 10",
    "condition_type": "record_count"
  }
}
```

### Backend Execution

- Condition evaluated once per execution
- Result determines which output path executes
- Both outputs receive same input data
- Only one path executes (not both)
- Expression evaluated as JavaScript
- Has access to `data` variable
- Must return boolean
- Errors default to false path

**Frontend Connection:**
Conditional nodes have two handles:
- `true` handle (typically green, top)
- `false` handle (typically red, bottom)

---

# Output Nodes

Output nodes are terminal nodes that save workflow results.

---

## 10. Output Node (`output`)

### Overview

| Property | Value |
|----------|-------|
| **Node Type** | `output` |
| **Name** | Output |
| **Description** | Save processed data to destination |
| **Icon** | `output` (Material Icons) |
| **Category** | `data_sink` |
| **Use Case** | Write workflow results to database, file, or API |

### Frontend Expected Structure

```json
{
  "id": "output-1",
  "type": "output",
  "position": {"x": 1000, "y": 200},
  "config": {
    "output_type": "database",
    "credential_id": 5,
    "table_name": "processed_results"
  }
}
```

### Configuration Fields

| Field Name | Type | Required | Default | Conditional | Validation |
|------------|------|----------|---------|-------------|------------|
| `output_type` | `select` | ✅ Yes | - | - | Must be valid type |
| `credential_id` | `credential_select` | ✅ Conditional | - | `output_type == "database"` | Valid RDBMS credential |
| `table_name` | `text` | ✅ Conditional | - | `output_type == "database"` | Non-empty string |
| `file_path` | `text` | ✅ Conditional | - | `output_type == "file"` | Non-empty string |
| `file_format` | `select` | ✅ Conditional | - | `output_type == "file"` | Must be csv or json |

#### Field Details

**output_type:**
- **Label:** "Output Type"
- **Placeholder:** "Select output type"
- **Help:** "Choose where to save the processed data"
- **Frontend Component:** Select dropdown
- **Options:**
  - `database` - Database Table
  - `file` - File (CSV/JSON)
  - `api` - API Endpoint

**credential_id (database mode):**
- **Label:** "Database Connection"
- **Placeholder:** "Select a database credential"
- **Help:** "Database connection for saving data"
- **Frontend Component:** Credential selector dropdown
- **Category Filter:** `RDBMS`
- **Shown When:** `output_type == "database"`

**table_name (database mode):**
- **Label:** "Table Name"
- **Placeholder:** "output_table"
- **Help:** "Name of the table to save data to"
- **Frontend Component:** Text input
- **Shown When:** `output_type == "database"`

**file_path (file mode):**
- **Label:** "File Path"
- **Placeholder:** "/path/to/output.csv"
- **Help:** "Path where the file should be saved"
- **Frontend Component:** Text input
- **Shown When:** `output_type == "file"`

**file_format (file mode):**
- **Label:** "File Format"
- **Placeholder:** "Select format"
- **Help:** "Format for the output file"
- **Frontend Component:** Select dropdown
- **Options:**
  - `csv` - CSV
  - `json` - JSON
- **Shown When:** `output_type == "file"`

### Inputs

| Input Name | Type | Description |
|------------|------|-------------|
| `data` | `any` | Data to be saved |

### Outputs

**None** - Output nodes are terminal (no outgoing connections).

### Example Configurations

#### Database Output

```json
{
  "type": "output",
  "config": {
    "output_type": "database",
    "credential_id": 5,
    "table_name": "processed_customers"
  }
}
```

#### File Output (CSV)

```json
{
  "type": "output",
  "config": {
    "output_type": "file",
    "file_path": "/data/output/results_2024.csv",
    "file_format": "csv"
  }
}
```

#### File Output (JSON)

```json
{
  "type": "output",
  "config": {
    "output_type": "file",
    "file_path": "/data/output/results.json",
    "file_format": "json"
  }
}
```

### Backend Execution

**Database Output:**
- Connects to database using `credential_id`
- Inserts data into `table_name`
- Table must exist or be auto-created (configurable)
- Supports INSERT or UPSERT operations
- Schema matching recommended

**File Output:**
- Writes data to `file_path`
- Directory must exist
- CSV format: comma delimiter, header row
- JSON format: array of objects
- File permissions must allow writing

---

# Appendices

## Frontend Field Types Reference

| Field Type | Component | Purpose | Example |
|------------|-----------|---------|---------|
| `text` | Text input | Single line text | Name, path |
| `textarea` | Textarea | Multi-line text | Description, SQL query |
| `number` | Number input | Numeric values with min/max | Batch size, timeout |
| `select` | Dropdown | Single choice from options | Language, format |
| `checkbox` | Checkbox | Boolean toggle | Enabled flag |
| `code_editor` | Code editor | Code with syntax highlighting | Script, JSON |
| `credential_select` | Credential dropdown | Select database/API credential | Database connection |
| `agent_select` | Agent dropdown | Select AI agent | Agent selection |
| `mcp_server_multi_select` | Multi-select | Multiple MCP servers | Tool attachment |
| `internal_tool_multi_select` | Multi-select with pairing | Tools + credentials | Tool attachment |
| `placeholder_mapping` | Key-value mapper | Map query placeholders | Dynamic values |
| `input_mapping` | Field mapper | Map input to agent fields | Agent inputs |
| `filter_conditions` | Condition builder | Build filter conditions | Data filtering |

## Conditional Field Visibility

Fields can be conditionally shown/hidden based on another field's value:

```json
{
  "name": "credential_id",
  "type": "credential_select",
  "conditional": {
    "field": "output_type",
    "value": "database"
  }
}
```

**Behavior:**
- Field only appears when `output_type == "database"`
- Field is required only when visible
- Validation runs only when visible

## Validation Rules

### Required Fields
- Must have non-empty value
- Empty strings, null, undefined are invalid
- Validation error shown in red below field

### Number Fields
- Must be numeric
- Must be within min/max range if specified
- Integer or decimal depending on configuration

### Credential/Agent Selection
- Selected ID must exist in database
- Selected resource must be active
- User must have access permissions

### Cron Expression Validation
- Must match cron syntax: `minute hour day month weekday`
- 5 parts separated by spaces
- Each part must be valid (* or number or range)

## Node Connection Rules

### Valid Connections

| Source Node Type | Can Connect To |
|------------------|----------------|
| `trigger_manual` | Any data source or processor |
| `trigger_schedule` | Any data source or processor |
| `trigger_chat` | Any data source or processor |
| `database` | Agent, Filter, Script, Conditional, Output |
| `agent` | Filter, Script, Conditional, Output, Agent (chaining) |
| `toolbox` | Agent (provides tools) |
| `filter` | Agent, Script, Conditional, Output |
| `script` | Agent, Filter, Conditional, Output |
| `conditional` (true) | Any processor or output |
| `conditional` (false) | Any processor or output |
| `output` | None (terminal) |

### Connection Constraints

1. **Trigger nodes:** Must be first node (no incoming connections)
2. **Output nodes:** Must be last node (no outgoing connections)
3. **Toolbox nodes:** Connect between data source and agent
4. **Conditional nodes:** Must have both true AND false paths defined
5. **Circular connections:** Not allowed
6. **One trigger per workflow:** Required

---

**End of Workflow Nodes Documentation**
