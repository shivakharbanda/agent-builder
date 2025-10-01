# Agent Builder Meta-Agent FastAPI Service

A FastAPI-based service that provides an interactive meta-agent for building custom AI agent configurations. The meta-agent interviews users through a structured conversation to collect agent specifications and outputs a complete agent configuration JSON.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Reference](#api-reference)
- [Usage Examples](#usage-examples)
- [Integration Guide](#integration-guide)
- [Troubleshooting](#troubleshooting)

## Overview

The Agent Builder Meta-Agent is a conversational AI service that guides users through creating custom agent configurations. It asks targeted questions to collect:

1. **Return Type**: Conversational vs. structured/workflow agents
2. **Agent Name**: A concise identifier
3. **Description**: One-sentence agent purpose
4. **System Prompt**: The agent's role and behavior instructions
5. **User Prompt**: Template for user interactions
6. **Schema Definition**: JSON Schema for structured output (if applicable)

The service outputs a complete agent configuration JSON that can be used to instantiate custom agents in other systems.

## Architecture

### Multi-Session Design

The service supports multiple concurrent sessions, allowing:
- **Session Isolation**: Each conversation is independent
- **Session Persistence**: Conversations can be resumed
- **Concurrent Users**: Multiple users/tabs without interference
- **Stateless Operations**: Each request includes session context

### Core Components

```
├── Session Management     # UUID-based session creation
├── Message Persistence    # SQLite storage with session scoping
├── Meta-Agent Engine     # Gemini-powered conversation flow
├── Configuration Parser  # JSON extraction and validation
└── API Layer            # FastAPI endpoints with CORS
```

## Installation

### Prerequisites

- Python 3.11+
- Virtual environment (recommended)
- Google API Key for Gemini

### Setup Steps

1. **Clone and navigate to the directory:**
   ```bash
   cd agent_maker_fastapi
   ```

2. **Create and activate virtual environment:**
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/Mac
   # or
   .venv\Scripts\activate     # Windows
   ```

3. **Install dependencies:**
   ```bash
   pip install fastapi uvicorn pydantic-ai aiosqlite python-dotenv
   # or if using uv:
   cd .. && uv sync && cd agent_maker_fastapi
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

## Configuration

### Environment Variables

Create a `.env` file in the project root:

```env
# Google API Configuration
GOOGLE_API_KEY=your_google_api_key_here

# Model Configuration
MODEL_NAME=gemini-1.5-flash

# Database Configuration
DB_PATH=messages.db

# Server Configuration
HOST=0.0.0.0
PORT=8001
```

### Getting Google API Key

1. Visit [Google AI Studio](https://aistudio.google.com)
2. Create a new API key
3. Add it to your `.env` file

## API Reference

### Base URL

```
http://localhost:8001
```

### Endpoints

#### 1. Health Check

**GET `/healthz`**

Returns server health status.

```bash
curl http://localhost:8001/healthz
```

**Response:**
```
ok
```

#### 2. Create Session

**POST `/session/`**

Creates a new conversation session and returns a unique session ID.

```bash
curl -X POST http://localhost:8001/session/
```

**Response:**
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

#### 3. Send Chat Message

**POST `/chat/`**

Sends a message to the meta-agent within a specific session. Returns a streaming response.

**Request Body:**
```json
{
  "prompt": "I want to build a customer service agent",
  "session_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Example:**
```bash
curl -N -X POST http://localhost:8001/chat/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "I want to build a workflow agent", "session_id": "your-session-id"}'
```

**Response:**
Streaming JSONL format with real-time message updates:
```
{"role": "user", "timestamp": "2024-01-01T12:00:00Z", "content": "I want to build a workflow agent"}
{"role": "model", "timestamp": "2024-01-01T12:00:01Z", "content": "Great! Do you want a 'conversational' agent or a 'workflow' (deterministic) agent?"}
```

#### 4. Get Chat History

**GET `/chat/?session_id={session_id}`**

Retrieves the complete conversation history for a session.

```bash
curl "http://localhost:8001/chat/?session_id=your-session-id"
```

**Response:**
JSONL format with all messages:
```
{"role": "user", "timestamp": "2024-01-01T12:00:00Z", "content": "I want to build an agent"}
{"role": "model", "timestamp": "2024-01-01T12:00:01Z", "content": "What type of agent would you like?"}
```

#### 5. Get Final Configuration

**GET `/finalize/?session_id={session_id}`**

Attempts to extract the final agent configuration JSON from the conversation.

```bash
curl "http://localhost:8001/finalize/?session_id=your-session-id"
```

**Response (when ready):**
```json
{
  "name": "CustomerServiceAgent",
  "description": "An agent that helps customers with support inquiries",
  "return_type": "structured",
  "prompts": [
    {
      "prompt_type": "system",
      "content": "You are a helpful customer service agent for {company_name}.",
      "placeholders": {
        "company_name": "Provide the company name"
      }
    },
    {
      "prompt_type": "user",
      "content": "Customer inquiry: {customer_message}",
      "placeholders": {
        "customer_message": "Provide the customer's message"
      }
    }
  ],
  "schema_definition": {
    "type": "object",
    "properties": {
      "response": {"type": "string"},
      "priority": {"type": "string", "enum": ["low", "medium", "high"]},
      "category": {"type": "string"}
    },
    "required": ["response", "priority"]
  }
}
```

**Response (not ready):**
```
Status: 202 Accepted
Content: "Not finalized yet."
```

#### 6. Generate Agent (Conversational)

**POST `/generate/`**

Conversational agent generation that asks focused questions then outputs final config JSON. Uses sessions like `/chat/` but with a specialized generator agent.

**Request Body:**
```json
{
  "prompt": "I need an agent to handle customer support tickets",
  "session_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

**Example Conversation:**
```bash
# Create session first
SESSION_ID=$(curl -s -X POST http://localhost:8001/session/ | jq -r '.session_id')

# Start the generation conversation
curl -N -X POST http://localhost:8001/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"I need an agent to categorize customer support emails\", \"session_id\": \"$SESSION_ID\"}"

# Agent might ask: "What categories should it use? Should it return structured data for integration?"

# You respond with clarifications
curl -N -X POST http://localhost:8001/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Categories: billing, technical, general. Yes, structured data for our CRM\", \"session_id\": \"$SESSION_ID\"}"

# Agent generates final config JSON when satisfied
```

**Response:**
Streaming JSONL format with questions, then final JSON config when ready.

**Get Final Configuration:**
```bash
curl "http://localhost:8001/generate/finalize/?session_id=$SESSION_ID"
```

#### 7. Reset Session

**POST `/reset/`**

Clears all messages for a specific session.

**Request Body:**
```json
{
  "session_id": "123e4567-e89b-12d3-a456-426614174000"
}
```

```bash
curl -X POST http://localhost:8001/reset/ \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your-session-id"}'
```

**Response:**
```
OK
```

## Usage Examples

### Focused Agent Generation (Recommended)

The `/generate/` endpoint provides conversational agent generation that asks targeted questions then outputs the final config:

```bash
# Example 1: Customer Service Agent
SESSION_ID=$(curl -s -X POST http://localhost:8001/session/ | jq -r '.session_id')

# Start conversation
curl -N -X POST http://localhost:8001/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"I need a customer service agent for billing inquiries\", \"session_id\": \"$SESSION_ID\"}"

# Agent asks: "What specific billing tasks should it handle? Should it return structured data?"
# You respond:
curl -N -X POST http://localhost:8001/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Handle payment questions, account balance checks, escalate disputes. Yes, structured for CRM integration\", \"session_id\": \"$SESSION_ID\"}"

# Agent generates final config
curl "http://localhost:8001/generate/finalize/?session_id=$SESSION_ID"

# Example 2: Content Moderation
SESSION_ID=$(curl -s -X POST http://localhost:8001/session/ | jq -r '.session_id')

curl -N -X POST http://localhost:8001/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Build a content moderation agent for user posts\", \"session_id\": \"$SESSION_ID\"}"

# Example 3: Email Classification
SESSION_ID=$(curl -s -X POST http://localhost:8001/session/ | jq -r '.session_id')

curl -N -X POST http://localhost:8001/generate/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Email classifier for support department routing\", \"session_id\": \"$SESSION_ID\"}"
```

### Complete Agent Creation Workflow (Interactive)

#### 1. Start a New Session

```bash
# Create session
RESPONSE=$(curl -s -X POST http://localhost:8001/session/)
SESSION_ID=$(echo $RESPONSE | jq -r '.session_id')
echo "Session ID: $SESSION_ID"
```

#### 2. Begin Conversation

```bash
# Start the agent building process
curl -N -X POST http://localhost:8001/chat/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"I want to build an agent\", \"session_id\": \"$SESSION_ID\"}"
```

#### 3. Follow the Interview Process

The meta-agent will ask questions in sequence. Respond to each:

```bash
# Question 1: Agent type
curl -N -X POST http://localhost:8001/chat/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"workflow\", \"session_id\": \"$SESSION_ID\"}"

# Question 2: Agent name
curl -N -X POST http://localhost:8001/chat/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"EmailClassifier\", \"session_id\": \"$SESSION_ID\"}"

# Question 3: Description
curl -N -X POST http://localhost:8001/chat/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Classifies emails by priority and department\", \"session_id\": \"$SESSION_ID\"}"

# Question 4: System prompt
curl -N -X POST http://localhost:8001/chat/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"You are an email classification agent for {company}. Analyze emails and categorize them.\", \"session_id\": \"$SESSION_ID\"}"

# Question 5: User prompt
curl -N -X POST http://localhost:8001/chat/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"Email content: {email_content}\", \"session_id\": \"$SESSION_ID\"}"

# Question 6: JSON Schema (for structured agents)
curl -N -X POST http://localhost:8001/chat/ \
  -H "Content-Type: application/json" \
  -d "{\"prompt\": \"{\\\\"type\\\\":\\\\"object\\\\",\\\\"properties\\\\":{\\\\"priority\\\\":{\\\\"type\\\\":\\\\"string\\\\",\\\\"enum\\\\":[\\\\"low\\\\",\\\\"medium\\\\",\\\\"high\\\\"]},\\\\"department\\\\":{\\\\"type\\\\":\\\\"string\\\\"}},\\\\"required\\\\":[\\\\"priority\\\\",\\\\"department\\\\"]}\", \"session_id\": \"$SESSION_ID\"}"
```

#### 4. Get Final Configuration

```bash
# Extract the final agent configuration
curl "http://localhost:8001/finalize/?session_id=$SESSION_ID"
```

### JavaScript/TypeScript Integration

```typescript
class AgentBuilderClient {
  private baseUrl: string;
  private sessionId: string | null = null;

  constructor(baseUrl: string = 'http://localhost:8001') {
    this.baseUrl = baseUrl;
  }

  // Conversational generation (recommended)
  async generateAgent(prompt: string, sessionId?: string): Promise<ReadableStream> {
    if (!sessionId) {
      sessionId = await this.createSession();
    }

    const response = await fetch(`${this.baseUrl}/generate/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ prompt, session_id: sessionId })
    });

    if (!response.ok) {
      throw new Error(`Generation failed: ${response.status}`);
    }

    return response.body!;
  }

  async finalizeGeneration(sessionId: string): Promise<any> {
    const response = await fetch(
      `${this.baseUrl}/generate/finalize/?session_id=${sessionId}`
    );

    if (response.status === 202) {
      throw new Error('Agent configuration not ready yet');
    }

    return response.json();
  }

  async createSession(): Promise<string> {
    const response = await fetch(`${this.baseUrl}/session/`, {
      method: 'POST'
    });
    const data = await response.json();
    this.sessionId = data.session_id;
    return this.sessionId;
  }

  async sendMessage(prompt: string): Promise<ReadableStream> {
    if (!this.sessionId) {
      throw new Error('No active session. Call createSession() first.');
    }

    const response = await fetch(`${this.baseUrl}/chat/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        prompt,
        session_id: this.sessionId
      })
    });

    return response.body!;
  }

  async getHistory(): Promise<any[]> {
    if (!this.sessionId) {
      throw new Error('No active session.');
    }

    const response = await fetch(
      `${this.baseUrl}/chat/?session_id=${this.sessionId}`
    );
    const text = await response.text();

    return text.trim().split('\\n').map(line => JSON.parse(line));
  }

  async finalize(): Promise<any> {
    if (!this.sessionId) {
      throw new Error('No active session.');
    }

    const response = await fetch(
      `${this.baseUrl}/finalize/?session_id=${this.sessionId}`
    );

    if (response.status === 202) {
      throw new Error('Agent configuration not ready yet');
    }

    return response.json();
  }

  async reset(): Promise<void> {
    if (!this.sessionId) {
      throw new Error('No active session.');
    }

    await fetch(`${this.baseUrl}/reset/`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        session_id: this.sessionId
      })
    });
  }
}

// Usage examples
const client = new AgentBuilderClient();

// Single-shot generation (recommended)
async function generateQuickAgent() {
  try {
    const config = await client.generateAgent(
      "Create a customer support agent that handles billing questions and escalates complex issues"
    );
    console.log('Generated agent configuration:', config);
    return config;
  } catch (error) {
    console.error('Generation failed:', error);
  }
}

// Interactive session (for complex requirements)
async function buildAgentInteractively() {
  // Create session
  await client.createSession();

  // Start conversation
  const stream = await client.sendMessage("I want to build an agent");

  // Process streaming response
  const reader = stream.getReader();
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    const text = new TextDecoder().decode(value);
    const lines = text.split('\\n').filter(line => line.trim());

    for (const line of lines) {
      try {
        const message = JSON.parse(line);
        console.log(`${message.role}: ${message.content}`);
      } catch (e) {
        // Ignore parsing errors for partial chunks
      }
    }
  }

  // Continue conversation based on agent responses...

  // Get final configuration
  try {
    const config = await client.finalize();
    console.log('Agent configuration:', config);
  } catch (error) {
    console.log('Configuration not ready yet');
  }
}
```

### Python Client Integration

```python
import requests
import json
import uuid
from typing import Dict, Any, Optional, Generator

class AgentBuilderClient:
    def __init__(self, base_url: str = "http://localhost:8001"):
        self.base_url = base_url
        self.session_id: Optional[str] = None

    def generate_agent(self, spec: str) -> Dict[str, Any]:
        """Generate agent configuration from specification (single-shot)."""
        response = requests.post(
            f"{self.base_url}/generate/",
            json={"spec": spec}
        )
        response.raise_for_status()
        return response.json()

    def create_session(self) -> str:
        """Create a new conversation session."""
        response = requests.post(f"{self.base_url}/session/")
        response.raise_for_status()
        data = response.json()
        self.session_id = data["session_id"]
        return self.session_id

    def send_message(self, prompt: str) -> Generator[Dict[str, Any], None, None]:
        """Send a message and yield streaming responses."""
        if not self.session_id:
            raise ValueError("No active session. Call create_session() first.")

        response = requests.post(
            f"{self.base_url}/chat/",
            json={"prompt": prompt, "session_id": self.session_id},
            stream=True
        )
        response.raise_for_status()

        for line in response.iter_lines():
            if line:
                try:
                    yield json.loads(line.decode('utf-8'))
                except json.JSONDecodeError:
                    continue

    def get_history(self) -> list[Dict[str, Any]]:
        """Get the complete conversation history."""
        if not self.session_id:
            raise ValueError("No active session.")

        response = requests.get(
            f"{self.base_url}/chat/",
            params={"session_id": self.session_id}
        )
        response.raise_for_status()

        lines = response.text.strip().split('\\n')
        return [json.loads(line) for line in lines if line.strip()]

    def finalize(self) -> Dict[str, Any]:
        """Get the final agent configuration."""
        if not self.session_id:
            raise ValueError("No active session.")

        response = requests.get(
            f"{self.base_url}/finalize/",
            params={"session_id": self.session_id}
        )

        if response.status_code == 202:
            raise ValueError("Agent configuration not ready yet")

        response.raise_for_status()
        return response.json()

    def reset(self) -> None:
        """Reset the current session."""
        if not self.session_id:
            raise ValueError("No active session.")

        response = requests.post(
            f"{self.base_url}/reset/",
            json={"session_id": self.session_id}
        )
        response.raise_for_status()

# Usage examples

# Single-shot generation (recommended)
def generate_quick_agent():
    client = AgentBuilderClient()

    spec = """
    Create a customer service chatbot for an e-commerce platform that can:
    - Handle order status inquiries
    - Process return requests
    - Escalate complex issues to human agents
    Should return structured data for our CRM integration.
    """

    try:
        config = client.generate_agent(spec)
        print("Generated Agent Configuration:")
        print(json.dumps(config, indent=2))
        return config
    except Exception as e:
        print(f"Generation failed: {e}")

# Interactive session (for complex requirements)
def build_agent_interactive():
    client = AgentBuilderClient()
    client.create_session()

    print("Agent Builder Started!")
    print("Type your responses to build your agent. Type 'quit' to exit.\\n")

    # Start the process
    for message in client.send_message("I want to build an agent"):
        if message["role"] == "model":
            print(f"Assistant: {message['content']}")
            break

    while True:
        user_input = input("You: ").strip()
        if user_input.lower() == 'quit':
            break

        print()  # Add spacing

        for message in client.send_message(user_input):
            if message["role"] == "model":
                print(f"Assistant: {message['content']}")

        # Check if we can finalize
        try:
            config = client.finalize()
            print("\\n" + "="*50)
            print("AGENT CONFIGURATION COMPLETE!")
            print("="*50)
            print(json.dumps(config, indent=2))
            break
        except ValueError:
            continue  # Not ready yet

    print("\\nThank you for using Agent Builder!")

if __name__ == "__main__":
    # Quick generation example
    generate_quick_agent()

    # Uncomment for interactive mode
    # build_agent_interactive()
```

## Integration Guide

### Frontend Integration Patterns

#### React Hook Example

```tsx
import { useState, useCallback } from 'react';

interface Message {
  role: 'user' | 'model';
  content: string;
  timestamp: string;
}

interface AgentConfig {
  name: string;
  description: string;
  return_type: 'structured' | 'unstructured';
  prompts: Array<{
    prompt_type: string;
    content: string;
    placeholders: Record<string, string>;
  }>;
  schema_definition?: object;
}

export const useAgentBuilder = (baseUrl: string = 'http://localhost:8001') => {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [config, setConfig] = useState<AgentConfig | null>(null);

  const createSession = useCallback(async () => {
    const response = await fetch(`${baseUrl}/session/`, { method: 'POST' });
    const data = await response.json();
    setSessionId(data.session_id);
    setMessages([]);
    setConfig(null);
    return data.session_id;
  }, [baseUrl]);

  const sendMessage = useCallback(async (prompt: string) => {
    if (!sessionId) throw new Error('No active session');

    setIsLoading(true);

    try {
      const response = await fetch(`${baseUrl}/chat/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt, session_id: sessionId })
      });

      const reader = response.body?.getReader();
      if (!reader) throw new Error('No response body');

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        const text = new TextDecoder().decode(value);
        const lines = text.split('\\n').filter(line => line.trim());

        for (const line of lines) {
          try {
            const message = JSON.parse(line);
            setMessages(prev => {
              const existing = prev.find(m =>
                m.role === message.role &&
                m.timestamp === message.timestamp
              );
              return existing ? prev : [...prev, message];
            });
          } catch (e) {
            // Ignore malformed JSON
          }
        }
      }

      // Check if configuration is ready
      await checkFinalization();
    } finally {
      setIsLoading(false);
    }
  }, [sessionId, baseUrl]);

  const checkFinalization = useCallback(async () => {
    if (!sessionId) return;

    try {
      const response = await fetch(
        `${baseUrl}/finalize/?session_id=${sessionId}`
      );

      if (response.ok) {
        const configData = await response.json();
        setConfig(configData);
      }
    } catch (e) {
      // Configuration not ready yet
    }
  }, [sessionId, baseUrl]);

  const reset = useCallback(async () => {
    if (!sessionId) return;

    await fetch(`${baseUrl}/reset/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId })
    });

    setMessages([]);
    setConfig(null);
  }, [sessionId, baseUrl]);

  return {
    sessionId,
    messages,
    isLoading,
    config,
    createSession,
    sendMessage,
    reset
  };
};
```

### Backend Integration

#### Express.js Proxy Example

```javascript
const express = require('express');
const { createProxyMiddleware } = require('http-proxy-middleware');

const app = express();

// Proxy agent builder requests
app.use('/api/agent-builder', createProxyMiddleware({
  target: 'http://localhost:8001',
  changeOrigin: true,
  pathRewrite: {
    '^/api/agent-builder': '',
  },
}));

// Custom endpoint to save completed agents
app.post('/api/agents', express.json(), async (req, res) => {
  const { session_id } = req.body;

  try {
    // Get the final configuration
    const response = await fetch(
      `http://localhost:8001/finalize/?session_id=${session_id}`
    );

    if (response.status === 202) {
      return res.status(400).json({ error: 'Agent not finalized yet' });
    }

    const agentConfig = await response.json();

    // Save to your database
    const savedAgent = await saveAgentToDatabase(agentConfig);

    res.json(savedAgent);
  } catch (error) {
    res.status(500).json({ error: error.message });
  }
});

async function saveAgentToDatabase(config) {
  // Your database logic here
  // Return the saved agent with ID
}
```

### Docker Deployment

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install -r requirements.txt

# Copy application
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV HOST=0.0.0.0
ENV PORT=8001

# Expose port
EXPOSE 8001

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \\
  CMD curl -f http://localhost:8001/healthz || exit 1

# Run application
CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8001"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  agent-builder:
    build: .
    ports:
      - "8001:8001"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - MODEL_NAME=gemini-1.5-flash
      - DB_PATH=/app/data/messages.db
    volumes:
      - agent-builder-data:/app/data
    restart: unless-stopped

volumes:
  agent-builder-data:
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

# Verify the key is valid by testing it directly
curl -H "Authorization: Bearer YOUR_API_KEY" \\
  "https://generativelanguage.googleapis.com/v1beta/models"
```

#### 2. "Unknown extension ?R" Regex Error

**Problem**: Python's regex engine doesn't support recursive patterns.

**Solution**: This should be fixed in the current version. If you encounter it:
```python
# Replace the problematic regex in app.py
JSON_RE = re.compile(r"\\{[^{}]*(?:\\{[^{}]*\\}[^{}]*)*\\}\\s*$", re.DOTALL)
```

#### 3. Session Not Found

**Problem**: Session ID is invalid or expired.

**Solution**:
```bash
# Create a new session
curl -X POST http://localhost:8001/session/

# Verify the session works
curl "http://localhost:8001/chat/?session_id=your-new-session-id"
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

#### 5. Port Already in Use

**Problem**: Port 8001 is already occupied.

**Solution**:
```bash
# Find what's using the port
lsof -i :8001

# Use a different port
uvicorn app:app --host 0.0.0.0 --port 8002

# Or update your .env file
echo "PORT=8002" >> .env
```

### Performance Considerations

#### 1. Database Optimization

For production use, consider:
- Regular database cleanup of old sessions
- Indexing optimization for large datasets
- Connection pooling

```python
# Add to your production setup
import asyncio
from datetime import datetime, timedelta

async def cleanup_old_sessions():
    """Remove sessions older than 24 hours"""
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM messages WHERE created_at < ?",
            (cutoff.isoformat(),)
        )
        await db.commit()

# Run cleanup periodically
asyncio.create_task(cleanup_old_sessions())
```

#### 2. Rate Limiting

For production deployment:

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.post("/chat/")
@limiter.limit("10/minute")
async def post_chat(request: Request, body: ChatRequest):
    # Your existing implementation
```

### Development Tips

#### 1. Debug Mode

```bash
# Run with debug logging
uvicorn app:app --host 0.0.0.0 --port 8001 --reload --log-level debug
```

#### 2. Testing with Different Models

```bash
# Try different Gemini models
export MODEL_NAME=gemini-1.5-pro
export MODEL_NAME=gemini-1.0-pro
```

#### 3. Mock Responses for Testing

```python
# Add to app.py for testing
import os

if os.getenv("MOCK_MODE") == "true":
    class MockAgent:
        async def run_stream(self, prompt, message_history=None):
            # Return mock responses for testing
            pass

    meta_agent = MockAgent()
```

This documentation provides everything needed to understand, deploy, and integrate the Agent Builder Meta-Agent service. For additional support or questions, refer to the API endpoints for real-time interaction capabilities.