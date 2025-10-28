# Workflow Chat Service (Simplified v2)

A simplified conversational service with session management, designed for frontend integration.

## Overview

This is a **basic skeleton** version that provides:
- ✅ Simple conversational agent (Gemini-powered)
- ✅ Session-based message persistence
- ✅ Streaming responses for real-time chat
- ✅ Core API endpoints for frontend integration
- ❌ **No workflow building features** (those will be designed from scratch later)

## Architecture

```
workflow_maker_fastapi_v2/
├── app.py          # Main FastAPI app (~250 lines)
├── .env            # Environment configuration
├── run.sh          # Startup script
├── README.md       # This file
└── messages.db     # SQLite (created on startup)
```

### Key Simplifications vs v1

| Feature | v1 (Complex) | v2 (Simplified) |
|---------|--------------|-----------------|
| Agent System | Multi-agent (supervisor + worker) | Single simple agent |
| Tools | 4 workflow tools | None |
| Output | Structured responses | Plain text |
| Code Structure | ~1500 lines, 3 modules | ~250 lines, 1 file |
| Purpose | Complex workflow building | Simple chat only |

## Installation

### Prerequisites
- Python 3.11+
- Google API Key (Gemini)

### Setup

1. **Navigate to directory:**
   ```bash
   cd workflow_maker_fastapi_v2
   ```

2. **Configure environment:**
   ```bash
   # Edit .env with your configuration
   nano .env
   ```

   Required settings:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   MODEL_NAME=gemini-1.5-flash-latest
   DB_PATH=messages.db
   PORT=8002
   ```

3. **Run the service:**
   ```bash
   ./run.sh
   ```

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
# Response: ok
```

#### 2. Create Session
**POST `/session/`**

Initialize a new chat session with a session_id from Django.

```bash
curl -X POST http://localhost:8002/session/ \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-session-123"}'

# Response:
# {
#   "session_id": "test-session-123",
#   "status": "initialized"
# }
```

#### 3. Generate Chat Response
**POST `/generate/`**

Send a message and receive streaming response.

```bash
curl -N -X POST http://localhost:8002/generate/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello! How can you help me?", "session_id": "test-session-123"}'

# Response (streaming JSONL):
# {"role": "user", "timestamp": "2025-01-01T12:00:00Z", "content": "Hello! How can you help me?"}
# {"role": "assistant", "timestamp": "2025-01-01T12:00:01Z", "content": "Hi", "delta": true}
# {"role": "assistant", "timestamp": "2025-01-01T12:00:01Z", "content": "!", "delta": true}
# ...
```

**Request Body:**
```json
{
  "prompt": "User message here",
  "session_id": "session-id-from-django"
}
```

**Response Format:**
- Streaming JSONL (newline-delimited JSON)
- Each line is a JSON object
- User message echoed first
- Assistant response streamed in chunks (`delta: true`)

#### 4. Finalize (Placeholder)
**GET `/generate/finalize/?session_id={session_id}`**

Placeholder endpoint for future workflow finalization.

```bash
curl "http://localhost:8002/generate/finalize/?session_id=test-session-123"

# Response (202 Accepted):
# "Not implemented yet. This endpoint will be used for workflow finalization."
```

#### 5. Reset Session
**POST `/reset/`**

Clear all messages for a session.

```bash
curl -X POST http://localhost:8002/reset/ \
  -H "Content-Type: application/json" \
  -d '{"session_id": "test-session-123"}'

# Response: OK
```

## Usage Example

### Complete Chat Flow

```bash
# 1. Create session
SESSION_ID=$(curl -s -X POST http://localhost:8002/session/ \
  -H "Content-Type: application/json" \
  -d '{"session_id": "demo-session"}' | jq -r '.session_id')

echo "Session ID: $SESSION_ID"

# 2. Send first message
curl -N -X POST http://localhost:8002/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Hello! Can you help me understand workflows?\", \"session_id\": \"$SESSION_ID\"}"

# 3. Send follow-up (message history is preserved)
curl -N -X POST http://localhost:8002/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"What features will be available later?\", \"session_id\": \"$SESSION_ID\"}"

# 4. Reset conversation
curl -X POST http://localhost:8002/reset/ \
  -H "Content-Type: application/json" \
  -d "{\"session_id\": \"$SESSION_ID\"}"
```

## Session Management

### How It Works

1. **Session Creation**: Frontend creates session via Django, then initializes FastAPI session
2. **Message Persistence**: All messages stored in SQLite per session
3. **Conversation Context**: Message history loaded for each request
4. **Usage Tracking**: Token usage tracked per session (in-memory)

### Database Schema

```sql
CREATE TABLE messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL,
  session_id TEXT NOT NULL,
  blob BLOB NOT NULL
);

CREATE INDEX idx_messages_session_id ON messages(session_id);
```

## Integration with Frontend

This service is designed to integrate with the Agent Builder UI:

1. Frontend creates session via Django backend
2. Django creates session_id and calls `POST /session/`
3. User chats with AI via `POST /generate/` (streaming)
4. AI provides helpful conversational responses
5. Workflow building features will be added later in redesign

## What's NOT Included

This simplified version **intentionally excludes**:
- ❌ Workflow building tools
- ❌ Database/agent discovery
- ❌ Schema inspection
- ❌ Structured outputs
- ❌ Multi-agent orchestration
- ❌ Node/edge management

These features will be **designed from scratch** later based on new requirements.

## Development

### Running in Development

```bash
# With auto-reload
cd workflow_maker_fastapi_v2
uvicorn app:app --host 0.0.0.0 --port 8002 --reload
```

### Viewing Logs

The service prints helpful logs:
```
🤖 SIMPLE CHAT AGENT INITIALIZED
   Model: gemini-1.5-flash-latest
   Mode: Basic conversation (no tools)

✅ Database initialized

📝 New session initialized: session-123

💬 Chat request - Session: session-123
   Prompt: Hello! How can you help me?
   Loaded 0 messages from history
   ✅ Response sent and persisted
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GOOGLE_API_KEY` | (required) | Google API key for Gemini |
| `MODEL_NAME` | `gemini-1.5-flash-latest` | Gemini model to use |
| `DB_PATH` | `messages.db` | SQLite database path |
| `PORT` | `8002` | Server port |
| `HOST` | `0.0.0.0` | Server host |
| `DJANGO_API_BASE` | `http://localhost:8000` | Django backend URL (unused in v2) |

## Comparison: v1 vs v2

### Lines of Code
- **v1**: ~1500 lines (app.py + agents + models)
- **v2**: ~250 lines (app.py only)

### Complexity
- **v1**: Multi-agent system, 4 tools, structured outputs, task queues
- **v2**: Single agent, no tools, plain text, simple chat

### Purpose
- **v1**: Build workflows through conversational AI with autonomous tool execution
- **v2**: Simple chat interface ready for frontend integration

## Next Steps

To add workflow building features:

1. Design new architecture (simple, not over-engineered)
2. Define clear requirements for workflow building
3. Implement incrementally in v2
4. Test with frontend integration

This simplified version provides a **clean foundation** without the complexity that caused issues in v1.

## Troubleshooting

### Common Issues

**"GOOGLE_API_KEY not set"**
```bash
# Check .env file
cat .env | grep GOOGLE_API_KEY

# Verify key is valid
curl -H "Authorization: Bearer YOUR_API_KEY" \
  "https://generativelanguage.googleapis.com/v1beta/models"
```

**Port already in use**
```bash
# Find process on port 8002
lsof -i :8002

# Use different port
uvicorn app:app --host 0.0.0.0 --port 8003
```

**Database locked**
```bash
# Check for locks
lsof messages.db

# Reset database
rm messages.db
# Restart service (will recreate)
```

## License

Part of the Agent Builder project.

---

**Built with:** FastAPI, PydanticAI, Gemini, SQLite
