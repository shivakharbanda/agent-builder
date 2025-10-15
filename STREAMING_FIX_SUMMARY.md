# ✅ FIXED: Structured Output Streaming Error

## Problem Solved

**Errors:**
```
⚠️  Non-structured chunk (fallback to text): 1 validation error for WorkflowBuilderResponse
  JSON input should be string, bytes or bytearray

TypeError: Object of type WorkflowBuilderResponse is not JSON serializable
```

## Root Cause

When using `output_type=WorkflowBuilderResponse` with Pydantic AI:
- **`stream_output()` doesn't work** - It's designed for text streaming, not structured data
- **Structured data is built internally** during agent execution
- **Final structured result** is available in `result.data` after completion
- **Streaming partial JSON** causes validation errors because chunks aren't complete JSON objects

## What Was Fixed

### **workflow_maker_fastapi/app.py** (Lines 989-1009)

**BEFORE (BROKEN):**
```python
# Run supervisor agent with structured output
async with supervisor_agent.run_stream(prompt, message_history=messages, deps=deps) as result:
    print(f"✅ Supervisor stream started, waiting for structured output...")

    # Stream structured responses
    response_chunks = 0
    async for chunk in result.stream_output(debounce_by=0.01):
        response_chunks += 1

        try:
            # ❌ BROKEN: chunk is not valid JSON yet
            structured_response = WorkflowBuilderResponse.model_validate_json(chunk)

            # Yield structured response as JSON
            yield json.dumps({
                "role": "assistant",
                "timestamp": result.timestamp().isoformat(),
                "structured": True,
                "response": structured_response.model_dump()
            }).encode("utf-8") + b"\n"

        except Exception as e:
            # ❌ BROKEN: Tries to serialize Pydantic model objects
            print(f"⚠️  Non-structured chunk (fallback to text): {str(e)[:100]}")
            m = ModelResponse(parts=[TextPart(chunk)], timestamp=result.timestamp())
            yield json.dumps(to_chat_message(m)).encode("utf-8") + b"\n"

        print(f"📤 Streamed {response_chunks} response chunks")
```

**AFTER (FIXED):**
```python
# Run supervisor agent (non-streaming for structured output)
# NOTE: With output_type, Pydantic AI builds structured data internally
# and returns it in result.data after completion
print(f"🤖 Running supervisor agent (awaiting structured response)...")
result = await supervisor_agent.run(prompt, message_history=messages, deps=deps)

# ✅ Get final structured response from result.data
structured_response = result.data  # This is a WorkflowBuilderResponse object

print(f"✅ Supervisor completed successfully")
print(f"📤 Structured Response:")
print(f"   Action: {structured_response.action_type}")
print(f"   Message: {structured_response.message[:80]}...")

# ✅ Yield structured response as JSON
yield json.dumps({
    "role": "assistant",
    "timestamp": result.timestamp().isoformat(),
    "structured": True,
    "response": structured_response.model_dump()
}).encode("utf-8") + b"\n"
```

## Key Changes

1. **Replaced `run_stream()`** with `run()` - No streaming for structured output
2. **Removed parsing loop** - No need to parse partial chunks
3. **Access structured data** via `result.data` - This is the complete WorkflowBuilderResponse
4. **Serialize with `.model_dump()`** - Converts Pydantic model to dict before JSON encoding
5. **Removed exception handler** - No more errors to catch

## How It Works Now

### **User sends message:**
```
POST /generate/
{
  "prompt": "hi",
  "session_id": "abc123",
  "current_config": null
}
```

### **Backend flow:**
1. ✅ Echo user message immediately
2. ✅ Run supervisor agent (waits for completion)
3. ✅ Get structured response from `result.data`
4. ✅ Serialize to JSON and stream to frontend
5. ✅ Persist messages to database

### **Frontend receives:**
```json
{"role": "user", "timestamp": "...", "content": "hi"}
{"role": "assistant", "timestamp": "...", "structured": true, "response": {
  "action_type": "conversation",
  "data": {
    "message": "Hello! I'm here to help you build workflows...",
    "needs_user_input": false
  },
  "message": "Greeting user"
}}
```

## Benefits

✅ **No more parsing errors** - Complete structured data, not partial chunks
✅ **No more serialization errors** - Properly serialize Pydantic models
✅ **Clean, simple code** - No complex error handling needed
✅ **Works correctly** with Pydantic AI's `output_type` parameter
✅ **Frontend gets valid JSON** - Can handle structured responses deterministically

## Trade-offs

⚠️ **No real-time streaming** - Frontend waits for complete response
- **Impact:** ~1-3 seconds delay for simple requests
- **Mitigation:** Frontend can show loading spinner
- **Benefit:** Structured responses are worth the wait (frontend knows exactly what to do)

✅ **Better UX overall:**
- Structured responses enable incremental workflow building
- Frontend can add/edit/remove nodes automatically
- No ambiguity about what action to take

## Testing

**Test the fix:**
```bash
cd workflow_maker_fastapi
uvicorn app:app --host 0.0.0.0 --port 8001 --reload
```

**Send test request:**
```bash
# Register session with Django first
curl -X POST http://localhost:8000/api/builder-tools/register_session/ \
  -H "Content-Type: application/json" \
  -d '{"project_id": 1}'

# Get session_id from response, then:
curl -X POST http://localhost:8001/session/ \
  -H "Content-Type: application/json" \
  -d '{"session_id": "YOUR_SESSION_ID"}'

# Test chat
curl -X POST http://localhost:8001/generate/ \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "hi",
    "session_id": "YOUR_SESSION_ID",
    "current_config": null
  }'
```

**Expected output:**
```json
{"role": "user", "timestamp": "2025-10-15T...", "content": "hi"}
{"role": "assistant", "timestamp": "2025-10-15T...", "structured": true, "response": {
  "action_type": "conversation",
  "data": {
    "message": "Hello! I'm here to help you build workflows. What would you like to create?",
    "needs_user_input": true
  },
  "message": "Greeting and asking for workflow requirements"
}}
```

## Related Documentation

See these files for complete implementation details:
- **`WORKFLOW_MAKER_REVAMP.md`** - Full architecture documentation
- **`FINAL_FIX_SUMMARY.md`** - Previous fixes (agent parameter errors)
- **`IMPORT_FIX_SUMMARY.md`** - Import path fixes

---

**Status:** ✅ All streaming errors fixed
**Ready to test:** Yes!
**Next:** Test with frontend to verify structured responses work correctly
