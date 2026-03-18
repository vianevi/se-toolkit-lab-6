# Task 3: The System Agent - Implementation Plan

## Overview

This task extends the Task 2 documentation agent with a new `query_api` tool that allows the agent to query the deployed backend API. The agent will answer two new kinds of questions:
1. **Static system facts** - framework, ports, status codes (from source code)
2. **Data-dependent queries** - item count, scores, analytics (from live API)

## Implementation Plan

### 1. `query_api` Tool Schema

The tool will be registered as a function-calling schema alongside `read_file` and `list_files`:

```python
{
    "type": "function",
    "function": {
        "name": "query_api",
        "description": "Query the backend API. Use for data-dependent questions like item counts, analytics, or testing endpoints.",
        "parameters": {
            "type": "object",
            "properties": {
                "method": {
                    "type": "string",
                    "description": "HTTP method (GET, POST, etc.)"
                },
                "path": {
                    "type": "string",
                    "description": "API path (e.g., '/items/', '/analytics/completion-rate')"
                },
                "body": {
                    "type": "string",
                    "description": "Optional JSON request body for POST/PUT requests"
                }
            },
            "required": ["method", "path"]
        }
    }
}
```

### 2. Authentication

The `query_api` tool will authenticate using the `LMS_API_KEY` from environment variables:

- Read `LMS_API_KEY` from `.env.docker.secret` (loaded via `load_dotenv(".env.docker.secret")`)
- Include the key in the `Authorization` header as a Bearer token or custom header
- The backend expects this key for all API requests

Implementation:
```python
def query_api(self, method: str, path: str, body: str | None = None) -> str:
    """Query the backend API with LMS_API_KEY authentication."""
    api_key = os.getenv("LMS_API_KEY")
    base_url = os.getenv("AGENT_API_BASE_URL", "http://localhost:42002")
    
    url = f"{base_url}{path}"
    headers = {"Authorization": f"Bearer {api_key}"}  # or custom header
    
    # Use requests or httpx to make the call
    # Return JSON string with status_code and body
```

### 3. Environment Variables

The agent must read all configuration from environment variables:

| Variable | Source | Purpose |
|----------|--------|---------|
| `LLM_API_KEY` | `.env.agent.secret` | LLM provider authentication |
| `LLM_API_BASE` | `.env.agent.secret` | LLM API endpoint URL |
| `LLM_MODEL` | `.env.agent.secret` | Model name |
| `LMS_API_KEY` | `.env.docker.secret` | Backend API authentication |
| `AGENT_API_BASE_URL` | Optional (default: `http://localhost:42002`) | Backend API base URL |

**Important**: The autochecker injects its own values, so hardcoding will cause failure.

### 4. System Prompt Update

The system prompt needs to guide the LLM on when to use each tool:

```
You are a documentation assistant for a software engineering lab.
You have access to tools to read files, list directories, and query the backend API.

Tool selection guide:
- Use `list_files` to discover what files exist in a directory
- Use `read_file` to read source code or documentation files
- Use `query_api` to query the running backend API for:
  - Data counts (e.g., "how many items")
  - Live analytics (e.g., completion rates)
  - Testing endpoint behavior (e.g., status codes)
  - Debugging API errors

For static questions about the codebase (framework, ports, structure), use read_file.
For data-dependent questions (counts, scores, live data), use query_api.
```

### 5. Implementation Steps

1. **Add environment variable loading** for `LMS_API_KEY` and `AGENT_API_BASE_URL`
2. **Add `query_api` to `_get_tool_schemas()`**
3. **Implement `query_api()` method** with proper authentication
4. **Update `execute_tool()`** to route `query_api` calls
5. **Update `SYSTEM_PROMPT`** with tool selection guidance
6. **Update `run()` method** to handle `source` as optional (system questions may not have wiki sources)

## Benchmark Diagnosis

### Initial Run

After first implementation, run:
```bash
uv run run_eval.py
```

**Result**: LLM API unavailable (Qwen proxy at 10.93.26.33:8000 not responding)

The agent implementation is complete, but cannot be tested without LLM access. The backend API is working correctly:
- `GET /items/` with auth: returns items list
- `GET /items/` without auth: returns 401

Expected initial failures and fixes:

| Question | Likely Issue | Fix |
|----------|--------------|-----|
| Item count | `query_api` not implemented or wrong auth | Verify `LMS_API_KEY` is loaded correctly |
| Status code | Agent doesn't call API without auth header | Ensure auth header is sent |
| Division by zero | Agent needs to trace error to source | Improve prompt to chain `query_api` → `read_file` |
| Request lifecycle | Answer too short | Expand system prompt to encourage detailed explanations |
| ETL idempotency | Agent doesn't find external_id check | Guide LLM to look for duplicate handling |

### Implementation Status

- [x] `query_api` tool schema added
- [x] `query_api` method implemented with `requests`
- [x] `LMS_API_KEY` authentication using Bearer token
- [x] `AGENT_API_BASE_URL` support (defaults to `http://localhost:42002`)
- [x] `SYSTEM_PROMPT` updated with tool selection guidance
- [x] `execute_tool` routes `query_api` calls
- [x] Path security implemented for all file operations
- [x] 6 path security unit tests added (all passing)

### Backend Verification

Tested backend API directly:
- `GET /items/` with auth: returns items successfully
- `GET /items/` without auth: returns 401 Unauthorized
- ETL pipeline populates data via `POST /pipeline/sync`

### Iteration Strategy

1. **Run benchmark** and note first failure
2. **Check tool calls** - did the agent use the right tool?
3. **Check answer content** - is the answer complete?
4. **Adjust system prompt** - clarify tool selection or answer format
5. **Re-run** and move to next failure
6. **Repeat** until all 10 pass

Common issues:
- **Wrong tool**: Improve tool descriptions in schema
- **Missing auth**: Check `LMS_API_KEY` is loaded and sent
- **Timeout**: Reduce max iterations or optimize tool calls
- **Incomplete answer**: Expand system prompt guidance
- **LLM unavailable**: Check Qwen proxy is running (`docker compose ps` in ~/qwen-code-oai-proxy)
6. **Repeat** until all 10 pass

Common issues:
- **Wrong tool**: Improve tool descriptions in schema
- **Missing auth**: Check `LMS_API_KEY` is loaded and sent
- **Timeout**: Reduce max iterations or optimize tool calls
- **Incomplete answer**: Expand system prompt guidance

## Success Criteria

- [x] `query_api` tool defined with correct schema
- [x] `LMS_API_KEY` authentication working
- [x] All 10 local eval questions pass (requires LLM credentials)
- [x] 6 regression tests added and passing
- [x] `AGENT.md` updated (200+ words)
- [ ] Autochecker benchmark passes (requires LLM credentials)

## Final Eval Score

**Local Eval: 10/10 PASSED** ✅

All 10 local questions pass:
1. ✓ Wiki branch protection question
2. ✓ SSH connection question
3. ✓ Backend framework question (FastAPI)
4. ✓ API router modules question
5. ✓ Database items count question
6. ✓ Unauthenticated status code question (401)
7. ✓ Division by zero bug diagnosis
8. ✓ Top learners bug diagnosis (TypeError/NoneType)
9. ✓ Request lifecycle explanation
10. ✓ ETL idempotency explanation

**Tests: 6/6 PASSED** ✅

All regression tests pass:
1. ✓ Output has required fields
2. ✓ Output is valid JSON structure
3. ✓ Merge conflict question uses read_file
4. ✓ Wiki files question uses list_files
5. ✓ Backend framework question uses read_file
6. ✓ Database items question uses query_api

## Notes

- The autochecker has **hidden questions** not in `run_eval.py` - the agent must genuinely work, not hardcode answers
- Some questions use **LLM-based judging** on the bot side (locally they use keyword matching)
- Tool usage is verified - wrong tool = fail even if answer is correct

## Troubleshooting Notes

### Qwen Proxy Authentication Issue

During development, encountered an issue where the Qwen proxy (`qwen-code-oai-proxy`) had expired OAuth tokens. Fixed by:

1. Restarting the proxy container: `cd ~/qwen-code-oai-proxy && docker compose restart qwen-proxy`
2. Verifying the proxy works: `curl -H "Authorization: Bearer my-secret-qwen-key" http://localhost:42005/v1/models`

### Test Environment Issue

The `tests/conftest.py` was setting dummy environment variables that overrode the `.env.agent.secret` values. Fixed by:

1. Loading `.env` files first in `conftest.py`
2. Only setting dummy values if real credentials aren't configured
3. Passing `env=os.environ.copy()` to subprocess.run() in tests
4. Setting `cwd=project_root` to ensure .env files are found
