# Agent Builder API Documentation

## Overview
The Agent Builder provides a REST API for managing AI agents, workflows, and data processing pipelines. This Phase 1 implementation focuses on CRUD operations for the core models.

## Base URL
```
http://localhost:8000/api/
```

## Authentication
Currently using Django REST Framework's session authentication. Include session cookies with requests or use the browsable API.

## Core Models Hierarchy
```
Project (Top Level)
├── Agents
│   ├── Prompts (system/user)
│   └── Tools (via AgentTool)
└── Workflows
    ├── Nodes (input/agent/output)
    │   └── PlaceholderMappings
    ├── DataSources
    └── OutputNodes
```

## API Endpoints

### Projects
- `GET /api/projects/` - List all projects
- `POST /api/projects/` - Create new project
- `GET /api/projects/{id}/` - Get project details
- `PUT /api/projects/{id}/` - Update project
- `DELETE /api/projects/{id}/` - Soft delete project
- `GET /api/projects/{id}/agents/` - Get project's agents
- `GET /api/projects/{id}/workflows/` - Get project's workflows

### Agents
- `GET /api/agents/` - List all agents
- `POST /api/agents/` - Create new agent
- `GET /api/agents/{id}/` - Get agent details (includes prompts & tools)
- `PUT /api/agents/{id}/` - Update agent
- `DELETE /api/agents/{id}/` - Soft delete agent
- `GET /api/agents/{id}/prompts/` - Get agent's prompts
- `GET /api/agents/{id}/tools/` - Get agent's tools

### Prompts
- `GET /api/prompts/` - List all prompts
- `POST /api/prompts/` - Create new prompt
- `GET /api/prompts/{id}/` - Get prompt details
- `PUT /api/prompts/{id}/` - Update prompt
- `DELETE /api/prompts/{id}/` - Soft delete prompt

### Tools
- `GET /api/tools/` - List all tools
- `POST /api/tools/` - Create new tool
- `GET /api/tools/{id}/` - Get tool details
- `PUT /api/tools/{id}/` - Update tool
- `DELETE /api/tools/{id}/` - Soft delete tool

### Agent-Tool Relationships
- `GET /api/agent-tools/` - List all agent-tool relationships
- `POST /api/agent-tools/` - Link agent to tool
- `GET /api/agent-tools/{id}/` - Get relationship details
- `PUT /api/agent-tools/{id}/` - Update relationship configuration
- `DELETE /api/agent-tools/{id}/` - Remove tool from agent

### Workflows
- `GET /api/workflows/` - List all workflows
- `POST /api/workflows/` - Create new workflow
- `GET /api/workflows/{id}/` - Get workflow details (includes nodes)
- `PUT /api/workflows/{id}/` - Update workflow
- `DELETE /api/workflows/{id}/` - Soft delete workflow
- `GET /api/workflows/{id}/nodes/` - Get workflow's nodes

### Data Sources
- `GET /api/data-sources/` - List all data sources
- `POST /api/data-sources/` - Create new data source
- `GET /api/data-sources/{id}/` - Get data source details
- `PUT /api/data-sources/{id}/` - Update data source
- `DELETE /api/data-sources/{id}/` - Soft delete data source

### Workflow Nodes
- `GET /api/workflow-nodes/` - List all workflow nodes
- `POST /api/workflow-nodes/` - Create new workflow node
- `GET /api/workflow-nodes/{id}/` - Get node details (includes mappings)
- `PUT /api/workflow-nodes/{id}/` - Update workflow node
- `DELETE /api/workflow-nodes/{id}/` - Soft delete workflow node
- `GET /api/workflow-nodes/{id}/mappings/` - Get node's placeholder mappings

### Placeholder Mappings
- `GET /api/placeholder-mappings/` - List all placeholder mappings
- `POST /api/placeholder-mappings/` - Create new mapping
- `GET /api/placeholder-mappings/{id}/` - Get mapping details
- `PUT /api/placeholder-mappings/{id}/` - Update mapping
- `DELETE /api/placeholder-mappings/{id}/` - Soft delete mapping

### Output Nodes
- `GET /api/output-nodes/` - List all output nodes
- `POST /api/output-nodes/` - Create new output node
- `GET /api/output-nodes/{id}/` - Get output node details
- `PUT /api/output-nodes/{id}/` - Update output node
- `DELETE /api/output-nodes/{id}/` - Soft delete output node

## Sample API Usage

### Create a Project
```bash
curl -X POST http://localhost:8000/api/projects/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Call Center Analytics",
    "description": "Intent classification for customer service calls"
  }'
```

### Create an Agent
```bash
curl -X POST http://localhost:8000/api/agents/ \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Intent Classifier",
    "description": "Classifies customer intent from transcripts",
    "return_type": "structured",
    "schema_definition": {
      "type": "object",
      "properties": {
        "intent": {"type": "string"},
        "confidence": {"type": "number"}
      }
    },
    "project": 1
  }'
```

### Create Prompts for Agent
```bash
# System Prompt
curl -X POST http://localhost:8000/api/prompts/ \
  -H "Content-Type: application/json" \
  -d '{
    "agent": 1,
    "prompt_type": "system",
    "content": "You are an expert at analyzing customer calls. Classify intent: {categories}",
    "placeholders": {"categories": "Available intent categories"}
  }'

# User Prompt
curl -X POST http://localhost:8000/api/prompts/ \
  -H "Content-Type: application/json" \
  -d '{
    "agent": 1,
    "prompt_type": "user",
    "content": "Call ID: {call_id}\nTranscript: {transcript}",
    "placeholders": {
      "call_id": "Unique call identifier",
      "transcript": "Call transcript text"
    }
  }'
```

## Filtering & Search

All list endpoints support:
- **Filtering**: `?field=value` (e.g., `?project=1&is_active=true`)
- **Search**: `?search=term` (searches configured fields)
- **Ordering**: `?ordering=field` or `?ordering=-field` for descending

Examples:
```bash
# Filter agents by project and return type
GET /api/agents/?project=1&return_type=structured

# Search projects by name
GET /api/projects/?search=analytics

# Order workflows by creation date (newest first)
GET /api/workflows/?ordering=-created_at
```

## Sample Data

Load the included sample data for call center use case:
```bash
python manage.py load_sample_data
```

This creates:
- Admin user (username: `admin`, password: `admin123`)
- Call Center Analytics project
- Intent Classifier agent with prompts
- OpenAI GPT-4 tool configuration
- Complete workflow with data mappings

## Next Steps (Phase 2)
- Workflow execution engine
- Real-time data processing
- Agent orchestration
- Monitoring and logging
- API rate limiting and caching