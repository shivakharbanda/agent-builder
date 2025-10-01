# Workflow Builder AI Service

A FastAPI-based service that provides an interactive AI assistant for building workflow configurations. The assistant interviews users through a structured conversation to collect workflow specifications and outputs a complete workflow configuration JSON.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [Troubleshooting](#troubleshooting)

## Overview

The Workflow Builder AI Service is a conversational AI that guides users through creating custom workflow configurations. It asks targeted questions to collect:

1. **Data Source**: Where data comes from (database, API, file)
2. **Processing Steps**: What operations process the data (agents, filters, scripts)
3. **Destination**: Where results are saved (database, file, API)
4. **Flow Logic**: Conditional branching, transformations, etc.

The service outputs a complete workflow configuration JSON with nodes, edges, and execution properties.

## Architecture

### Multi-Session Design

The service supports multiple concurrent sessions:
- **Session Isolation**: Each conversation is independent
- **Session Persistence**: Conversations can be resumed
- **Concurrent Users**: Multiple users/tabs without interference
- **Stateless Operations**: Each request includes session context

### Core Components

```
├── Session Management     # UUID-based session creation
├── Message Persistence    # SQLite storage with session scoping
├── Generator Agent        # Gemini-powered conversation flow
├── Workflow Parser        # JSON extraction and validation
└── API Layer             # FastAPI endpoints with CORS
```

## Installation

### Prerequisites

- Python 3.11+
- Virtual environment (recommended)
- Google API Key for Gemini

### Setup Steps

1. **Navigate to the directory:**
   ```bash
   cd workflow_maker_fastapi
   ```

2. **Install dependencies:**
   ```bash
   # Using parent project's uv environment
   cd .. && uv sync && cd workflow_maker_fastapi

   # OR install directly with pip
   pip install fastapi uvicorn pydantic-ai aiosqlite python-dotenv
   ```

3. **Configure environment:**
   ```bash
   # Edit .env with your configuration
   nano .env
   ```

## Configuration

### Environment Variables

Edit the `.env` file:

```env
# Google API Configuration
GOOGLE_API_KEY=your_google_api_key_here

# Model Configuration
MODEL_NAME=gemini-1.5-flash-latest

# Database Configuration
DB_PATH=messages.db

# Server Configuration
HOST=0.0.0.0
PORT=8002
```

### Getting Google API Key

1. Visit [Google AI Studio](https://aistudio.google.com)
2. Create a new API key
3. Add it to your `.env` file

## API Reference

### Base URL

```
http://localhost:8002
```

### Endpoints

#### 1. Health Check

**GET `/healthz`**

Returns server health status.

```bash
curl http://localhost:8002/healthz
```

**Response:**
```
ok
```

#### 2. Create Session

**POST `/session/`**

Creates a new conversation session and returns a unique session ID.

```bash
curl -X POST http://localhost:8002/session/
```

**Response:**
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

#### 3. Generate Workflow

**POST `/generate/`**

Generates workflow configuration through conversational interaction. Returns streaming response.

**Request Body:**
```json
{
  "prompt": "I need to build a workflow for intent analysis",
  "session_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Example:**
```bash
curl -N -X POST http://localhost:8002/generate/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Build a workflow for customer sentiment analysis", "session_id": "your-session-id"}'
```

**Response:**
Streaming JSONL format with real-time message updates:
```
{"role": "user", "timestamp": "2025-01-01T12:00:00Z", "content": "Build a workflow for customer sentiment analysis"}
{"role": "model", "timestamp": "2025-01-01T12:00:01Z", "content": "Great! Let me help you build a sentiment analysis workflow..."}
```

#### 4. Get Final Configuration

**GET `/generate/finalize/?session_id={session_id}`**

Attempts to extract the final workflow configuration JSON from the conversation.

```bash
curl "http://localhost:8002/generate/finalize/?session_id=your-session-id"
```

**Response (when ready):**
```json
{
  "name": "Customer Sentiment Analysis",
  "description": "Analyzes customer feedback sentiment and saves results",
  "nodes": [
    {
      "id": "node_1",
      "type": "database",
      "position": {"x": 100, "y": 200},
      "config": {
        "label": "Customer Feedback"
      }
    },
    {
      "id": "node_2",
      "type": "agent",
      "position": {"x": 400, "y": 200},
      "config": {
        "label": "Sentiment Analyzer"
      }
    },
    {
      "id": "node_3",
      "type": "output",
      "position": {"x": 700, "y": 200},
      "config": {
        "label": "Save Results"
      }
    }
  ],
  "edges": [
    {"id": "edge_1", "source": "node_1", "target": "node_2"},
    {"id": "edge_2", "source": "node_2", "target": "node_3"}
  ],
  "properties": {
    "timeout": 3600,
    "retry_count": 3
  }
}
```

**Response (not ready):**
```
Status: 202 Accepted
Content: "Not finalized yet."
```

#### 5. Reset Session

**POST `/reset/`**

Clears all messages for a specific session.

**Request Body:**
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

```bash
curl -X POST http://localhost:8002/reset/ \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your-session-id"}'
```

**Response:**
```
OK
```

## Usage Examples

### Example 1: Simple Intent Analysis Workflow

```bash
# Create session
SESSION_ID=$(curl -s -X POST http://localhost:8002/session/ | jq -r '.session_id')

# Start conversation
curl -N -X POST http://localhost:8002/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"I need to analyze customer message intent\", \"session_id\": \"$SESSION_ID\"}"

# AI might ask: "Where is the customer data stored? Which agent should analyze intent? Where should results go?"

# Respond with details
curl -N -X POST http://localhost:8002/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Data is in customer_messages table, use IntentClassifier agent, save to analyzed_intents table\", \"session_id\": \"$SESSION_ID\"}"

# AI presents preview and asks for confirmation
# You respond: "yes"

curl -N -X POST http://localhost:8002/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"yes\", \"session_id\": \"$SESSION_ID\"}"

# Get final configuration
curl "http://localhost:8002/generate/finalize/?session_id=$SESSION_ID"
```

### Example 2: Filtered Processing Workflow

```bash
SESSION_ID=$(curl -s -X POST http://localhost:8002/session/ | jq -r '.session_id')

curl -N -X POST http://localhost:8002/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Process only VIP customer orders with custom priority scoring\", \"session_id\": \"$SESSION_ID\"}"

# AI asks clarifying questions...
# You provide details...
# AI generates workflow with: Database → Filter → Script → Output
```

### Example 3: Branching Workflow

```bash
SESSION_ID=$(curl -s -X POST http://localhost:8002/session/ | jq -r '.session_id')

curl -N -X POST http://localhost:8002/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Route support tickets based on urgency - high priority to urgent_tickets table, low to standard_tickets\", \"session_id\": \"$SESSION_ID\"}"

# AI generates: Database → Agent → Conditional → [High Priority Output, Low Priority Output]
```

## Workflow Patterns

### Linear Flow
```
Database → Agent → Output
```
Use case: Simple data processing

### Filtered Flow
```
Database → Filter → Agent → Output
```
Use case: Process subset of data

### Branching Flow
```
Database → Agent → Conditional → [Output A, Output B]
```
Use case: Route data based on conditions

### Multi-Step Processing
```
Database → Agent 1 → Script → Agent 2 → Output
```
Use case: Complex transformations

## Node Types

| Type | Purpose | Category | Example Use |
|------|---------|----------|-------------|
| **database** | Read from database tables | Data Source | Fetch customer records |
| **agent** | AI/ML processing | Processor | Classify intent, sentiment analysis |
| **filter** | Filter data by conditions | Processor | Only active users |
| **script** | Custom Python/JS code | Processor | Calculate metrics |
| **conditional** | Branch execution | Control Flow | Route by priority |
| **output** | Save results | Data Sink | Write to database/file |

## Output JSON Schema

```typescript
interface WorkflowConfig {
  name: string;
  description: string;
  nodes: Node[];
  edges: Edge[];
  properties?: WorkflowProperties;
}

interface Node {
  id: string;                    // "node_1", "node_2", etc.
  type: string;                  // "database", "agent", "output", etc.
  position: {x: number, y: number};
  config: {
    label: string;               // Display name
    // Detailed config added by user in UI later
  };
}

interface Edge {
  id: string;                    // "edge_1", "edge_2", etc.
  source: string;                // Source node ID
  target: string;                // Target node ID
}

interface WorkflowProperties {
  timeout?: number;              // Seconds (default: 3600)
  retry_count?: number;          // Default: 3
  schedule?: string;             // Cron expression
  watermark_start_date?: string;
  watermark_end_date?: string;
  notification_email?: string;
}
```

## Troubleshooting

### Common Issues

#### 1. "GOOGLE_API_KEY not set" Error

**Problem**: The application can't find your Google API key.

**Solution**:
```bash
# Check if .env file exists and has the correct key
cat .env | grep GOOGLE_API_KEY

# Make sure you're running from the correct directory
ls -la app.py .env

# Verify the key is valid
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://generativelanguage.googleapis.com/v1beta/models"
```

#### 2. Port Already in Use

**Problem**: Port 8002 is already occupied.

**Solution**:
```bash
# Find what's using the port
lsof -i :8002

# Use a different port
uvicorn app:app --host 0.0.0.0 --port 8003

# Or update your .env file
echo "PORT=8003" >> .env
```

#### 3. Session Not Found

**Problem**: Session ID is invalid or expired.

**Solution**:
```bash
# Create a new session
curl -X POST http://localhost:8002/session/

# Verify the session works
curl "http://localhost:8002/generate/finalize/?session_id=your-new-session-id"
```

#### 4. Database Connection Issues

**Problem**: SQLite database can't be created or accessed.

**Solutions**:
```bash
# Check permissions
ls -la messages.db

# Verify directory is writable
touch test_file && rm test_file

# Check if database is locked
lsof messages.db
```

## Running the Service

### Start Server

```bash
# Using run.sh script
./run.sh

# Or directly with uvicorn
uvicorn app:app --host 0.0.0.0 --port 8002 --reload
```

### Verify Service

```bash
# Health check
curl http://localhost:8002/healthz

# Should return: ok
```

## Integration with Frontend

This service is designed to integrate with the Agent Builder UI:

1. Frontend creates session via `/session/`
2. User chats with AI via `/generate/`
3. AI asks questions, user provides details
4. AI presents preview and asks for confirmation
5. User confirms (e.g., "yes")
6. Frontend polls `/generate/finalize/` for final JSON
7. Frontend populates workflow canvas with nodes and edges
8. User configures node details in UI
9. Workflow saved to Django backend

## Development Tips

### Debug Mode

```bash
# Run with debug logging
uvicorn app:app --host 0.0.0.0 --port 8002 --reload --log-level debug
```

### Testing Different Models

```bash
# Try different Gemini models
export MODEL_NAME=gemini-1.5-pro
export MODEL_NAME=gemini-1.0-pro
```

## Performance Considerations

- Session cleanup: Old sessions remain in SQLite (consider cleanup job)
- Streaming responses: Uses server-sent events for real-time updates
- Connection pooling: SQLite uses file-based storage (single writer)
- Memory limits: Large conversations stored in database

## Security Notes

- **Production**: Set specific CORS origins (currently allows all `*`)
- **API Keys**: Never commit `.env` file to version control
- **HTTPS**: Use HTTPS in production (set secure cookies)
- **Rate Limiting**: Consider adding rate limiting for production

---

**End of Documentation**
