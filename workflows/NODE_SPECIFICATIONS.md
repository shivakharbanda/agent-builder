# Workflow Node Specifications

**Version:** 1.0
**Last Updated:** 2025-10-01

This document provides complete technical specifications for all workflow node types supported by the Agent Builder platform. Each node specification includes configuration fields, validation rules, input/output specifications, and example configurations.

---

## Table of Contents

1. [Database Node](#1-database-node)
2. [Agent Node](#2-agent-node)
3. [Output Node](#3-output-node)
4. [Filter Node](#4-filter-node)
5. [Script Node](#5-script-node)
6. [Conditional Node](#6-conditional-node)

---

## 1. Database Node

### Overview

| Property | Value |
|----------|-------|
| **Name** | Database |
| **Type** | `database` |
| **Description** | Connects to your database to read data |
| **Icon** | `storage` (Material Icons) |
| **Category** | `data_source` |
| **Purpose** | Fetch data from SQL databases using custom queries |

### Configuration Fields

| Field Name | Type | Label | Required | Validation | Default | Help Text |
|------------|------|-------|----------|------------|---------|-----------|
| `credential_id` | `credential_select` | Database Connection | ✅ Yes | Must be valid credential ID | - | Choose the database connection to use for this node |
| `query` | `textarea` | SQL Query | ✅ Yes | Non-empty string | - | Write your SQL query. Use {{placeholder}} for dynamic values that will be replaced at runtime |
| `placeholders` | `placeholder_mapping` | Dynamic Placeholders | ❌ No | - | - | Define the values for placeholders used in your query |

#### Field Details:

**credential_id:**
- **Type:** Credential selector dropdown
- **Category Filter:** `RDBMS` (Relational Database Management Systems)
- **Placeholder:** "Select a database credential"
- **Loads:** Credentials from `/api/credentials/credentials/` filtered by category

**query:**
- **Type:** Textarea
- **Rows:** 6
- **Placeholder:** `SELECT * FROM table WHERE column = {{placeholder}}`
- **Supports:** Dynamic placeholders using `{{placeholder_name}}` syntax

**placeholders:**
- **Type:** Placeholder mapping (custom field type)
- **Placeholder:** "Map placeholder values"
- **Maps:** Placeholder names in query to runtime values

### Input/Output Specifications

#### Inputs
This node has **no inputs** (it's a data source).

#### Outputs

| Output Name | Type | Description |
|-------------|------|-------------|
| `data` | `table` | Query results as table data (array of objects) |

### Example Configuration

```json
{
  "credential_id": 5,
  "query": "SELECT * FROM customers WHERE created_at > {{start_date}} AND status = {{status_filter}}",
  "placeholders": {
    "start_date": "2024-01-01",
    "status_filter": "active"
  }
}
```

### Execution Notes

- Node connects to database using credential_id
- Executes SQL query with placeholder substitution
- Returns results as array of row objects
- Supports all SQL operations supported by the database type
- Connection pooling should be used for efficiency
- Query timeout should be configurable at workflow level

---

## 2. Agent Node

### Overview

| Property | Value |
|----------|-------|
| **Name** | AI Agent |
| **Type** | `agent` |
| **Description** | Process data using an AI agent |
| **Icon** | `smart_toy` (Material Icons) |
| **Category** | `processor` |
| **Purpose** | Apply AI/ML processing to input data using configured agents |

### Configuration Fields

| Field Name | Type | Label | Required | Validation | Default | Help Text |
|------------|------|-------|----------|------------|---------|-----------|
| `agent_id` | `agent_select` | AI Agent | ✅ Yes | Must be valid agent ID | - | Choose which AI agent will process the input data |
| `input_mapping` | `input_mapping` | Input Data Mapping | ❌ No | - | - | Define how input data should be mapped to the agent's expected inputs |
| `batch_size` | `number` | Batch Size | ❌ No | Min: 1, Max: 1000 | 100 | Number of records to process at once |
| `timeout` | `number` | Timeout (seconds) | ❌ No | Min: 5, Max: 300 | 30 | Maximum time to wait for agent response |

#### Field Details:

**agent_id:**
- **Type:** Agent selector dropdown
- **Placeholder:** "Select an AI agent"
- **Loads:** Agents from `/api/agents/` endpoint
- **Displays:** Agent name and return type in dropdown

**input_mapping:**
- **Type:** Input mapping (custom field type)
- **Placeholder:** "Map input fields to agent inputs"
- **Purpose:** Maps incoming data fields to agent prompt placeholders

**batch_size:**
- **Type:** Number input
- **Placeholder:** "100"
- **Min Value:** 1
- **Max Value:** 1000
- **Default:** 100
- **Purpose:** Controls how many records are processed in parallel

**timeout:**
- **Type:** Number input
- **Placeholder:** "30"
- **Min Value:** 5 seconds
- **Max Value:** 300 seconds (5 minutes)
- **Default:** 30 seconds
- **Purpose:** Maximum time to wait for agent response per batch

### Input/Output Specifications

#### Inputs

| Input Name | Type | Description |
|------------|------|-------------|
| `data` | `any` | Input data to be processed by the agent (typically array of objects) |

#### Outputs

| Output Name | Type | Description |
|-------------|------|-------------|
| `result` | `any` | Processed data from the agent (structure depends on agent return type) |

### Example Configuration

```json
{
  "agent_id": 12,
  "input_mapping": {
    "customer_name": "name",
    "customer_email": "email",
    "order_details": "order_text"
  },
  "batch_size": 50,
  "timeout": 60
}
```

### Execution Notes

- Agent must exist and be active
- Input data is batched according to batch_size
- Each batch is processed sequentially or in parallel (configurable)
- Agent's prompt placeholders are filled using input_mapping
- Timeout applies per batch, not total execution
- Failed batches can be retried based on workflow properties
- Agent return type determines output structure

---

## 3. Output Node

### Overview

| Property | Value |
|----------|-------|
| **Name** | Output |
| **Type** | `output` |
| **Description** | Save processed data to destination |
| **Icon** | `output` (Material Icons) |
| **Category** | `data_sink` |
| **Purpose** | Write workflow results to various destinations (database, file, API) |

### Configuration Fields

#### Base Fields

| Field Name | Type | Label | Required | Validation | Default | Help Text |
|------------|------|-------|----------|------------|---------|-----------|
| `output_type` | `select` | Output Type | ✅ Yes | Must be one of: database, file, api | - | Choose where to save the processed data |

**output_type options:**
- `database` - Database Table
- `file` - File (CSV/JSON)
- `api` - API Endpoint

#### Conditional Fields (output_type = "database")

| Field Name | Type | Label | Required | Validation | Default | Help Text |
|------------|------|-------|----------|------------|---------|-----------|
| `credential_id` | `credential_select` | Database Connection | ✅ Yes | Valid credential ID | - | Database connection for saving data |
| `table_name` | `text` | Table Name | ✅ Yes | Non-empty string | - | Name of the table to save data to |

**credential_id (database mode):**
- **Category Filter:** `RDBMS`
- **Placeholder:** "Select a database credential"
- **Shows:** Only when output_type = "database"

**table_name:**
- **Type:** Text input
- **Placeholder:** "output_table"
- **Shows:** Only when output_type = "database"

#### Conditional Fields (output_type = "file")

| Field Name | Type | Label | Required | Validation | Default | Help Text |
|------------|------|-------|----------|------------|---------|-----------|
| `file_path` | `text` | File Path | ✅ Yes | Non-empty string | - | Path where the file should be saved |
| `file_format` | `select` | File Format | ✅ Yes | Must be: csv or json | - | Format for the output file |

**file_path:**
- **Type:** Text input
- **Placeholder:** "/path/to/output.csv"
- **Shows:** Only when output_type = "file"

**file_format:**
- **Type:** Select dropdown
- **Options:**
  - `csv` - CSV
  - `json` - JSON
- **Placeholder:** "Select format"
- **Shows:** Only when output_type = "file"

#### Conditional Fields (output_type = "api")

*Note: API output type is defined but fields are not yet implemented in nodeConfigs.json*

### Input/Output Specifications

#### Inputs

| Input Name | Type | Description |
|------------|------|-------------|
| `data` | `any` | Data to be saved (typically array of objects) |

#### Outputs
This node has **no outputs** (it's a data sink/terminal node).

### Example Configurations

#### Database Output

```json
{
  "output_type": "database",
  "credential_id": 3,
  "table_name": "processed_customers"
}
```

#### File Output (CSV)

```json
{
  "output_type": "file",
  "file_path": "/data/output/results_2024_10_01.csv",
  "file_format": "csv"
}
```

#### File Output (JSON)

```json
{
  "output_type": "file",
  "file_path": "/data/output/results.json",
  "file_format": "json"
}
```

### Execution Notes

- Output type determines which fields are required
- For database output:
  - Table must exist or be auto-created (configurable)
  - Schema matching is recommended
  - Supports INSERT or UPSERT operations
- For file output:
  - Directory must exist
  - File permissions must allow writing
  - CSV format uses comma delimiter with header row
  - JSON format creates array of objects
- API output type to be implemented

---

## 4. Filter Node

### Overview

| Property | Value |
|----------|-------|
| **Name** | Filter |
| **Type** | `filter` |
| **Description** | Filter and select data based on conditions |
| **Icon** | `filter_alt` (Material Icons) |
| **Category** | `processor` |
| **Purpose** | Filter incoming data rows based on conditional logic |

### Configuration Fields

| Field Name | Type | Label | Required | Validation | Default | Help Text |
|------------|------|-------|----------|------------|---------|-----------|
| `conditions` | `filter_conditions` | Filter Conditions | ✅ Yes | At least one condition | - | Define conditions to filter the data |
| `operator` | `select` | Condition Operator | ✅ Yes | Must be: AND or OR | AND | How to combine multiple conditions |

#### Field Details:

**conditions:**
- **Type:** Filter conditions (custom field type - array of condition objects)
- **Placeholder:** "Add filter conditions"
- **Structure:** Array of condition objects with field, operator, value

**operator:**
- **Type:** Select dropdown
- **Placeholder:** "AND"
- **Default:** "AND"
- **Options:**
  - `AND` - AND (all conditions must match)
  - `OR` - OR (any condition can match)

### Input/Output Specifications

#### Inputs

| Input Name | Type | Description |
|------------|------|-------------|
| `data` | `table` | Input data to be filtered (array of objects) |

#### Outputs

| Output Name | Type | Description |
|-------------|------|-------------|
| `data` | `table` | Filtered data (subset of input matching conditions) |

### Example Configuration

```json
{
  "conditions": [
    {
      "field": "age",
      "operator": ">",
      "value": 18
    },
    {
      "field": "status",
      "operator": "==",
      "value": "active"
    }
  ],
  "operator": "AND"
}
```

### Execution Notes

- Evaluates each row against all conditions
- AND operator: row must match ALL conditions to pass
- OR operator: row must match ANY condition to pass
- Supported comparison operators:
  - `==` (equals)
  - `!=` (not equals)
  - `>` (greater than)
  - `<` (less than)
  - `>=` (greater than or equal)
  - `<=` (less than or equal)
  - `contains` (string contains)
  - `startswith` (string starts with)
  - `endswith` (string ends with)
- Returns array of objects that match filter criteria
- Empty result if no rows match

---

## 5. Script Node

### Overview

| Property | Value |
|----------|-------|
| **Name** | Custom Script |
| **Type** | `script` |
| **Description** | Run custom Python or JavaScript code |
| **Icon** | `code` (Material Icons) |
| **Category** | `processor` |
| **Purpose** | Execute custom code for data transformation or business logic |

### Configuration Fields

| Field Name | Type | Label | Required | Validation | Default | Help Text |
|------------|------|-------|----------|------------|---------|-----------|
| `language` | `select` | Language | ✅ Yes | Must be: python or javascript | python | Programming language for the script |
| `script` | `code_editor` | Script Code | ✅ Yes | Non-empty string | - | Your custom code. Input data is available as 'data' variable |
| `timeout` | `number` | Timeout (seconds) | ❌ No | Min: 5, Max: 300 | 30 | Maximum execution time for the script |

#### Field Details:

**language:**
- **Type:** Select dropdown
- **Placeholder:** "Select language"
- **Default:** "python"
- **Options:**
  - `python` - Python
  - `javascript` - JavaScript

**script:**
- **Type:** Code editor (textarea with monospace font)
- **Rows:** 10
- **Placeholder:**
  ```python
  # Python code here
  def process(data):
      # Process your data
      return data
  ```
- **Available Variables:** `data` (input data from previous node)

**timeout:**
- **Type:** Number input
- **Placeholder:** "30"
- **Min Value:** 5 seconds
- **Max Value:** 300 seconds (5 minutes)
- **Default:** 30 seconds

### Input/Output Specifications

#### Inputs

| Input Name | Type | Description |
|------------|------|-------------|
| `data` | `any` | Input data for the script (available as 'data' variable) |

#### Outputs

| Output Name | Type | Description |
|-------------|------|-------------|
| `result` | `any` | Script execution result (return value from script) |

### Example Configurations

#### Python Example

```json
{
  "language": "python",
  "script": "def process(data):\n    # Add calculated field\n    for row in data:\n        row['total_value'] = row['quantity'] * row['price']\n    return data",
  "timeout": 60
}
```

#### JavaScript Example

```json
{
  "language": "javascript",
  "script": "function process(data) {\n    // Filter and transform\n    return data\n        .filter(row => row.status === 'active')\n        .map(row => ({\n            ...row,\n            fullName: `${row.firstName} ${row.lastName}`\n        }));\n}",
  "timeout": 30
}
```

### Execution Notes

- Script runs in isolated sandbox environment
- Python execution:
  - Python 3.x runtime
  - Limited standard library access (security)
  - No file system or network access
  - Input data passed as argument to `process()` function
- JavaScript execution:
  - Node.js runtime
  - Limited standard library
  - No file system or network access
  - Input data passed to `process()` function
- Script must return data (not modify in place)
- Timeout applies to total script execution
- Errors are caught and logged
- Memory limits apply (configurable)

---

## 6. Conditional Node

### Overview

| Property | Value |
|----------|-------|
| **Name** | Conditional |
| **Type** | `conditional` |
| **Description** | Branch workflow based on conditions |
| **Icon** | `fork_right` (Material Icons) |
| **Category** | `control_flow` |
| **Purpose** | Split workflow execution into different paths based on conditions |

### Configuration Fields

| Field Name | Type | Label | Required | Validation | Default | Help Text |
|------------|------|-------|----------|------------|---------|-----------|
| `condition` | `text` | Condition Expression | ✅ Yes | Non-empty string | - | JavaScript expression that evaluates to true/false |
| `condition_type` | `select` | Condition Type | ✅ Yes | Must be one of the options | expression | Type of condition to evaluate |

#### Field Details:

**condition:**
- **Type:** Text input
- **Placeholder:** "data.length > 0"
- **Purpose:** Expression that evaluates to boolean
- **Context:** Has access to `data` variable

**condition_type:**
- **Type:** Select dropdown
- **Placeholder:** "Select type"
- **Default:** "expression"
- **Options:**
  - `expression` - JavaScript Expression
  - `field_value` - Field Value Comparison
  - `record_count` - Record Count Check

### Input/Output Specifications

#### Inputs

| Input Name | Type | Description |
|------------|------|-------------|
| `data` | `any` | Input data to evaluate condition against |

#### Outputs

| Output Name | Type | Description |
|------------|------|-------------|
| `true` | `any` | Output when condition evaluates to true (passes data through) |
| `false` | `any` | Output when condition evaluates to false (passes data through) |

### Example Configurations

#### Expression Type

```json
{
  "condition": "data.length > 100",
  "condition_type": "expression"
}
```

#### Field Value Comparison

```json
{
  "condition": "data.status === 'approved'",
  "condition_type": "field_value"
}
```

#### Record Count Check

```json
{
  "condition": "data.length >= 10",
  "condition_type": "record_count"
}
```

### Execution Notes

- Condition is evaluated once per workflow execution
- Result determines which output path is taken
- Both outputs receive the same input data
- Only one output path executes (not both)
- Expression type:
  - Evaluated as JavaScript expression
  - Has access to `data` variable
  - Must return boolean
- Field value type:
  - Compares specific field value
  - Supports standard comparison operators
- Record count type:
  - Checks number of records in data array
  - Useful for empty set detection
- Errors in condition evaluation default to false path
- Supports nested conditional logic

---

## Node Connection Rules

### Valid Connections

| Source Node | Can Connect To |
|-------------|----------------|
| Database | Agent, Filter, Script, Conditional, Output |
| Agent | Filter, Script, Conditional, Output, Agent (chaining) |
| Filter | Agent, Script, Conditional, Output |
| Script | Agent, Filter, Conditional, Output |
| Conditional (true) | Any processor or output node |
| Conditional (false) | Any processor or output node |
| Output | *None* (terminal node) |

### Connection Constraints

- Output nodes cannot have outgoing connections (terminal nodes)
- Database nodes cannot have incoming connections (source nodes)
- Circular connections are not allowed
- Conditional nodes must have both true and false paths defined
- Each node can have multiple inputs (merged) or single input depending on configuration
- Data type compatibility should be validated

---

## Data Type Reference

### Type Definitions

| Type | Description | Example |
|------|-------------|---------|
| `any` | Any data type | `{...}`, `[...]`, `"string"`, `123` |
| `table` | Array of objects (rows) | `[{col1: val1, col2: val2}, ...]` |
| `string` | Text data | `"example text"` |
| `number` | Numeric data | `42`, `3.14` |
| `boolean` | True/false | `true`, `false` |
| `object` | Key-value pairs | `{key: "value"}` |
| `array` | List of values | `[1, 2, 3]` |

---

## Configuration Field Type Reference

### Field Types

| Field Type | Description | UI Component | Example |
|------------|-------------|--------------|---------|
| `text` | Single line text input | Text input | Name, path, expression |
| `textarea` | Multi-line text input | Textarea | SQL query, description |
| `number` | Numeric input with validation | Number input | Timeout, batch size |
| `select` | Dropdown selection | Select dropdown | Language, format, operator |
| `credential_select` | Credential selector | Searchable dropdown | Database connection |
| `agent_select` | Agent selector | Searchable dropdown | AI agent selection |
| `code_editor` | Code editor with syntax highlighting | Monospace textarea | Script code |
| `placeholder_mapping` | Dynamic placeholder mapper | Custom component | Query placeholders |
| `input_mapping` | Input field mapper | Custom component | Agent inputs |
| `filter_conditions` | Condition builder | Custom component | Filter conditions |

---

## Validation Rules Reference

### Required Field Validation
- Field must have non-empty value
- Empty strings, null, undefined are invalid
- For select fields, must select valid option

### Number Field Validation
- Value must be numeric
- Must be within min/max range if specified
- Integer or decimal depending on configuration

### Conditional Field Validation
- Only validated when condition is met
- Condition based on another field's value
- Field appears/disappears dynamically in UI

### Credential/Agent Selection Validation
- Selected ID must exist in database
- Selected resource must be active
- User must have access permissions

---

## Execution Context

### Runtime Variables

All nodes have access to:
- `data` - Input data from previous node
- `workflow_id` - Current workflow ID
- `execution_id` - Current execution ID
- `node_id` - Current node ID
- `config` - Node configuration object

### Error Handling

- Node execution failures are caught and logged
- Failed nodes can be retried based on workflow properties
- Error messages include node type, ID, and error details
- Workflow execution can continue or halt based on configuration

### Performance Considerations

- Large datasets should use batch processing
- Timeouts prevent infinite execution
- Connection pooling for database nodes
- Script execution is sandboxed
- Memory limits per node execution

---

## Appendix: Complete Node Configuration Examples

### Complex Workflow Example

```json
{
  "nodes": [
    {
      "id": "db-1",
      "type": "database",
      "config": {
        "credential_id": 5,
        "query": "SELECT * FROM orders WHERE created_at > {{start_date}}",
        "placeholders": {
          "start_date": "2024-01-01"
        }
      }
    },
    {
      "id": "filter-1",
      "type": "filter",
      "config": {
        "conditions": [
          {"field": "amount", "operator": ">", "value": 100}
        ],
        "operator": "AND"
      }
    },
    {
      "id": "agent-1",
      "type": "agent",
      "config": {
        "agent_id": 12,
        "batch_size": 50,
        "timeout": 60
      }
    },
    {
      "id": "output-1",
      "type": "output",
      "config": {
        "output_type": "database",
        "credential_id": 5,
        "table_name": "processed_orders"
      }
    }
  ],
  "edges": [
    {"source": "db-1", "target": "filter-1"},
    {"source": "filter-1", "target": "agent-1"},
    {"source": "agent-1", "target": "output-1"}
  ]
}
```

---

**End of Node Specifications Document**
