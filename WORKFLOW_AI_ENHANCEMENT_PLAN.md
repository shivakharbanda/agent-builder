# Workflow AI Enhancement Plan

**Project**: Agent Builder - Workflow Builder AI Auto-Configuration
**Date Created**: 2025-10-02
**Status**: Planning Phase

---

## Context & Background

### Current System Overview

**What We Have:**
- Visual workflow builder with drag-and-drop nodes (React Flow)
- AI chat interface that creates basic workflow structure
- Manual node configuration required after AI generation
- Three main node types: Database, Agent, Output

**The Problem:**
Currently, the AI agent (`workflow_maker_fastapi`) creates workflows with **empty configurations**:

```json
{
  "type": "database",
  "config": {
    "label": "Call Transcripts"  // ← Only has label, missing credential_id, query, etc.
  }
}
```

Users must **manually configure every field** after creation:
- Database nodes: Select credential, write SQL query
- Agent nodes: Select agent, set batch size, timeout
- Output nodes: Select output type, credential, table name

This takes **~10 clicks and 5 minutes per workflow**.

### The Vision

AI should create **fully configured workflows** by being intelligent about:
1. **Available credentials** - Auto-select the right database connection
2. **Database schema** - Auto-generate appropriate SQL queries
3. **Available agents** - Auto-select the right AI agent for the task
4. **Output configuration** - Auto-suggest output table names

**Target User Experience:**
```
User: "I need a workflow for sentiment analysis on call transcripts"
AI:
  ✓ Found credential: "Call Transcript DB" (ID: 3)
  ✓ Inspecting schema... found "call_transcripts" table
  ✓ Found agent: "Sentiment Analyzer" (ID: 3)
  ✓ Creating fully configured workflow...
User: Reviews, clicks Save (30 seconds total)
```

### Key System Components

**1. Backend (Django)**
- Location: `/workflows/` app
- Models: `Workflow`, `WorkflowNode`, `WorkflowProperties`
- API: Django REST Framework viewsets

**2. AI Service (FastAPI)**
- Location: `/workflow_maker_fastapi/`
- Port: `8002`
- LLM: Google Gemini
- Session-based chat with streaming responses

**3. Frontend (React)**
- Location: `/agent_builder_ui/app/`
- Component: `ChatInterface.tsx` (chat with AI)
- Component: `WorkflowCanvas.tsx` (visual builder)
- State: Workflow config with nodes/edges/properties

**4. Database Manager**
- Package: `dq_db_manager` (external dependency)
- GitHub: Custom package with PostgreSQL/MySQL handlers
- Key Feature: Metadata extraction (`metadata_extractor.py`)
- Can inspect: Tables, columns, relationships, sample data

### Available Resources

**Credentials API:**
- Endpoint: `/api/credentials/credentials/`
- Returns: All credentials with name, description, type, category
- Example: `{id: 3, name: "Call Transcript DB", type: "PostgreSQL"}`

**Agents API:**
- Endpoint: `/api/agents/`
- Returns: All agents with name, description, return type
- Example: `{id: 3, name: "Sentiment Analyzer", description: "..."}`

**Database Metadata Extraction:**
```python
from dq_db_manager.database_factory import DatabaseFactory
handler = DatabaseFactory.get_database_handler("postgresql", connection_details)
metadata = handler.metadata_extractor.extract_metadata()
# Returns: tables, columns, data types, sample data
```

---

## Implementation Phases

### Phase 1: Context Injection - Make AI Aware of Credentials & Agents

**Goal**: AI knows what credentials and agents exist in the system

**What to Build:**

1. **Django API Endpoint**
   - File: `workflows/views.py`
   - Endpoint: `GET /api/workflows/builder/context/?project_id={id}`
   - Returns:
     ```json
     {
       "credentials": [
         {"id": 3, "name": "Call Transcript DB", "type": "PostgreSQL", "description": "..."},
         {"id": 5, "name": "Analytics DB", "type": "MySQL", "description": "..."}
       ],
       "agents": [
         {"id": 3, "name": "Sentiment Analyzer", "description": "Analyzes sentiment..."},
         {"id": 7, "name": "Intent Classifier", "description": "Classifies intent..."}
       ]
     }
     ```

2. **workflow_maker_fastapi Updates**
   - File: `workflow_maker_fastapi/app.py`
   - On session creation (`POST /session/`):
     - Accept `project_id` parameter
     - Fetch context from Django API
     - Store in session state
   - Update system prompt:
     ```
     You have access to:
     CREDENTIALS: [list from API]
     AGENTS: [list from API]

     When user requests a workflow, consider available resources.
     ```

3. **Frontend Update**
   - File: `agent_builder_ui/app/components/workflow/ChatInterface.tsx`
   - Pass `project_id` when creating session
   - Add from URL params or context

**Success Criteria:**
- AI can reference credentials/agents by name in chat
- Example: "I found credential 'Call Transcript DB' that matches your request"
- Config is still empty (we'll populate it in later phases)

**Estimated Effort**: 2-3 hours
**Risk Level**: Low
**Dependencies**: None

---

### Phase 2: Smart Credential Matching

**Goal**: AI auto-fills `credential_id` in database and output nodes

**What to Build:**

1. **Enhanced LLM Prompt**
   - File: `workflow_maker_fastapi/app.py`
   - Update system prompt with matching rules:
     ```
     When creating database nodes:
     1. Match user's description to credential names/descriptions
     2. Consider keywords: table names, data types, use case
     3. Return credential_id in config

     Example:
     User: "process call transcripts"
     Match: "Call Transcript DB" (contains "call", "transcript")
     Config: {"credential_id": "3"}
     ```

2. **Response Format Update**
   - Ensure AI returns configs with `credential_id` field
   - Example output:
     ```json
     {
       "type": "database",
       "config": {
         "credential_id": "3"  // ← Auto-filled
       }
     }
     ```

**Success Criteria:**
- Database nodes have `credential_id` populated
- Output nodes (database type) have `credential_id` populated
- Matching is accurate >80% of the time

**Estimated Effort**: 1-2 hours
**Risk Level**: Low (prompt engineering only)
**Dependencies**: Phase 1

---

### Phase 3: Database Schema Inspection & Query Generation

**Goal**: AI auto-generates appropriate SQL queries based on schema

**What to Build:**

1. **Schema Inspection Endpoint**
   - File: `workflow_maker_fastapi/app.py`
   - Endpoint: `POST /inspect-schema/`
   - Request: `{"credential_id": 3}`
   - Implementation:
     ```python
     # Fetch credential from Django API
     credential = fetch_from_django(f"/api/credentials/credentials/{credential_id}/")

     # Use dq_db_manager to inspect
     handler = DatabaseFactory.get_database_handler(
         db_type=credential["type"].lower(),
         connection_details=credential["connection_details"]
     )
     metadata = handler.metadata_extractor.extract_metadata()

     return {
         "tables": metadata["tables"],
         "schema": {
             table_name: {
                 "columns": [...],
                 "sample_data": [...]
             }
         }
     }
     ```

2. **Update Workflow Generation Flow**
   - When database node is needed:
     - Call `/inspect-schema/` with matched credential
     - Inject schema into LLM context
     - AI generates SELECT query with appropriate columns

3. **Enhanced System Prompt**
   ```
   DATABASE SCHEMA (Credential: Call Transcript DB):
   Tables:
     - call_transcripts
       Columns: transcript_id (TEXT), transcript_text (TEXT), call_timestamp (TIMESTAMP)
       Sample: [{"transcript_id": "T001", "transcript_text": "Agent: Hello...", ...}]

   Generate SELECT queries that:
   - Include only necessary columns
   - Use proper table names
   - Consider data types
   ```

**Success Criteria:**
- Database nodes have valid SQL queries
- Queries select appropriate columns for the task
- No syntax errors in generated SQL

**Estimated Effort**: 3-4 hours
**Risk Level**: Medium (external dependency on dq_db_manager)
**Dependencies**: Phase 1, Phase 2

---

### Phase 4: Smart Agent Matching

**Goal**: AI auto-fills `agent_id`, `batch_size`, `timeout` in agent nodes

**What to Build:**

1. **Enhanced Agent Matching Prompt**
   - File: `workflow_maker_fastapi/app.py`
   - Update system prompt:
     ```
     AGENT MATCHING RULES:
     - Match task description to agent descriptions
     - Consider: sentiment → "Sentiment Analyzer"
     - Consider: intent → "Intent Classifier"
     - Consider: classification → agents with "classify" in description

     AGENT CONFIGURATION DEFAULTS:
     - batch_size: 5-10 (smaller for complex agents, larger for simple)
     - timeout: 30-60 seconds (longer for LLM-based agents)
     ```

2. **Response Format**
   ```json
   {
     "type": "agent",
     "config": {
       "agent_id": "3",           // ← Matched agent
       "batch_size": "5",         // ← Smart default
       "timeout": "30"            // ← Smart default
     }
   }
   ```

**Success Criteria:**
- Agent nodes have `agent_id` populated
- Batch size and timeout are reasonable defaults
- Agent matching is accurate >80% of the time

**Estimated Effort**: 1-2 hours
**Risk Level**: Low (prompt engineering only)
**Dependencies**: Phase 1

---

### Phase 5: Smart Output Configuration

**Goal**: AI auto-configures output nodes with sensible defaults

**What to Build:**

1. **Output Table Naming Logic**
   - File: `workflow_maker_fastapi/app.py`
   - Update system prompt:
     ```
     OUTPUT TABLE NAMING:
     Pattern: {input_table}_{task_type}_results

     Examples:
     - Input: call_transcripts, Task: sentiment → "sentiment_results"
     - Input: customer_data, Task: classification → "classification_results"
     - Input: logs, Task: analysis → "log_analysis_results"

     Always suggest table name, let user modify if needed.
     ```

2. **Output Type Selection**
   - Default to `database` if input is database
   - Default to `file` if user mentions export/download
   - Default to `api` if user mentions webhook/integration

3. **Response Format**
   ```json
   {
     "type": "output",
     "config": {
       "output_type": "database",
       "credential_id": "3",      // ← Same as input credential
       "table_name": "sentiment_results"  // ← Auto-suggested
     }
   }
   ```

**Success Criteria:**
- Output nodes have all required fields populated
- Table names follow logical naming convention
- Output type matches user intent

**Estimated Effort**: 1-2 hours
**Risk Level**: Low
**Dependencies**: Phase 1, Phase 2

---

### Phase 6: Frontend Polish & User Feedback

**Goal**: Show users what AI is doing, make process transparent

**What to Build:**

1. **Loading States**
   - File: `agent_builder_ui/app/components/workflow/ChatInterface.tsx`
   - Add visual feedback:
     - "🔍 Inspecting database schema..."
     - "🤖 Matching agents..."
     - "✨ Generating workflow..."

2. **Context Display in Chat**
   - Show matched resources:
     ```
     AI: I found these resources:
     ✓ Credential: Call Transcript DB (PostgreSQL)
     ✓ Agent: Sentiment Analyzer
     ✓ Tables: call_transcripts (50 rows)
     ```

3. **Config Highlighting in UI**
   - File: `agent_builder_ui/app/components/workflow/WorkflowCanvas.tsx`
   - Highlight auto-filled fields with badge:
     - "✨ Auto-configured by AI"
   - Allow users to edit any field

4. **Error Handling**
   - If schema inspection fails: "Couldn't inspect database, please configure manually"
   - If no agents match: "No matching agents found, please select manually"

**Success Criteria:**
- Users understand what AI is doing
- Loading states show progress
- Errors are handled gracefully
- Users can override AI decisions

**Estimated Effort**: 2-3 hours
**Risk Level**: Low
**Dependencies**: All previous phases

---

## Implementation Priority & Order

**Recommended Sequence:**

1. **Phase 1** (Context Injection) - FOUNDATION
   - Everything depends on this
   - Simple API + basic integration
   - Immediate visible improvement

2. **Phase 2** (Credential Matching) - QUICK WIN
   - Builds on Phase 1
   - Just prompt engineering
   - Delivers immediate value

3. **Phase 4** (Agent Matching) - PARALLEL TO PHASE 3
   - Can be done independently
   - Same pattern as credential matching
   - High user value

4. **Phase 3** (Schema Inspection) - COMPLEX
   - Requires external integration
   - Most technically challenging
   - Highest value-add

5. **Phase 5** (Output Config) - FINISHING TOUCH
   - Simple once previous phases done
   - Completes the auto-config story

6. **Phase 6** (Frontend Polish) - FINAL STEP
   - Makes everything user-friendly
   - Can iterate continuously

---

## Technical Notes & Considerations

### Security
- **Credential exposure**: Never send full connection strings to LLM
- Only send credential IDs and metadata (name, description, type)
- Schema inspection happens server-side only

### Performance
- **Schema inspection is slow**: Cache results per credential
- Invalidate cache when credentials change
- Set timeout limits on metadata extraction

### Error Handling
- **LLM failures**: Gracefully fall back to empty configs
- **Schema inspection failures**: Continue without query generation
- **API unavailability**: Show clear error messages

### Testing Strategy
- **Unit tests**: Each phase independently
- **Integration tests**: Full workflow generation flow
- **Manual tests**: Different workflow types (sentiment, classification, etc.)

### Rollout Strategy
- **Feature flag**: Enable AI auto-config per user/project
- **A/B testing**: Compare time-to-workflow with/without AI
- **Metrics**: Track auto-config accuracy, user edits, success rate

---

## Success Metrics

**Quantitative:**
- Time to create workflow: <1 minute (vs 5 minutes manual)
- Config accuracy: >80% fields correct without edits
- User edits per workflow: <2 (vs 10+ manual)

**Qualitative:**
- User feedback: "AI understood what I needed"
- Support tickets: Fewer questions about node configuration
- Adoption: More workflows created per user

---

## File Structure Reference

```
agent-builder/
├── workflows/                           # Django workflow app
│   ├── views.py                        # ← ADD: context API endpoint
│   ├── models.py                       # (existing models)
│   └── execution/                      # (workflow execution)
│
├── workflow_maker_fastapi/             # AI service
│   ├── app.py                          # ← MODIFY: context fetch, schema inspection
│   └── session_manager.py              # ← MODIFY: store context in session
│
├── agent_builder_ui/                   # React frontend
│   └── app/
│       ├── components/workflow/
│       │   ├── ChatInterface.tsx       # ← MODIFY: pass project_id
│       │   └── WorkflowCanvas.tsx      # ← MODIFY: highlight auto-configs
│       └── lib/
│           └── workflowBuilderApi.ts   # ← MODIFY: context API calls
│
└── WORKFLOW_AI_ENHANCEMENT_PLAN.md     # ← This file
```

---

## Next Steps

1. **Review this plan** - Ensure all stakeholders agree
2. **Start Phase 1** - Context injection (2-3 hours)
3. **Test thoroughly** - Before moving to next phase
4. **Iterate** - Based on user feedback

---

**Last Updated**: 2025-10-02
**Owner**: Development Team
**Review Date**: After each phase completion
