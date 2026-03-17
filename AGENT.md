# Lab Agent

A CLI tool that connects to an LLM and answers questions using tools. The agent can read files, list directories, and query the backend API to find accurate information from the project wiki and live system data.

## Architecture

### Task 1: Basic LLM Chat

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   User CLI  │────▶│   agent.py   │────▶│  LLM Provider   │
│  (question) │     │  (OpenAI SDK)│     │ (Qwen Code API) │
└─────────────┘     └──────────────┘     └─────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ .env.agent.  │
                    │   secret     │
                    └──────────────┘
```

### Task 2+: Agentic Loop with Tools

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   User CLI  │────▶│   agent.py   │────▶│  LLM Provider   │
│  (question) │     │  (Agentic    │     │ (Qwen Code API) │
└─────────────┘     │   Loop)      │     └─────────────────┘
                    │      │               │
                    │      ▼               │
                    │  ┌──────────┐        │
                    │  │ Tools:   │◀───────┘
                    │  │ - read   │
                    │  │ - list   │
                    │  │ - query  │
                    │  └──────────┘
                    │      │
                    │      ├──────► Project Files (wiki/, etc.)
                    │      └──────► Backend API
                    ▼
             JSON Output
```

### Task 3: System Agent with query_api

```
┌─────────────┐     ┌──────────────┐     ┌─────────────────┐
│   User CLI  │────▶│   agent.py   │────▶│  LLM Provider   │
│  (question) │     │  (Agentic    │     │ (Qwen Code API) │
└─────────────┘     │   Loop)      │     └─────────────────┘
                    │      │               │
                    │      ▼               │
                    │  ┌──────────────────┐
                    │  │ Tools:           │
                    │  │ - read_file      │──────► Local files
                    │  │ - list_files     │──────► Local directories
                    │  │ - query_api      │──────► Backend API (auth)
                    │  └──────────────────┘
                    ▼
             JSON Output
```

## LLM Provider

**Provider**: Qwen Code API (OpenAI-compatible endpoint)

**Model**: `qwen3-coder-plus`

**Why Qwen Code API**:
- 1000 free requests per day
- Works from Russia
- No credit card required
- OpenAI-compatible API (easy to switch providers)

**Alternative**: OpenRouter (free tier: 50 requests/day)

## Configuration

The agent reads configuration from environment variables loaded from two files:

### LLM Configuration (`.env.agent.secret`)

```bash
# LLM API key
LLM_API_KEY=your-api-key-here

# API base URL (OpenAI-compatible endpoint)
LLM_API_BASE=http://<vm-ip>:<port>/v1

# Model name
LLM_MODEL=qwen3-coder-plus
```

### Backend API Configuration (`.env.docker.secret`)

```bash
# Backend API key for query_api authentication
LMS_API_KEY=my-secret-api-key

# Optional: Backend API base URL (default: http://localhost:42002)
AGENT_API_BASE_URL=http://localhost:42002
```

### All Environment Variables

| Variable             | Source               | Purpose                                      |
| -------------------- | -------------------- | -------------------------------------------- |
| `LLM_API_KEY`        | `.env.agent.secret`  | LLM provider API key                         |
| `LLM_API_BASE`       | `.env.agent.secret`  | LLM API endpoint URL                         |
| `LLM_MODEL`          | `.env.agent.secret`  | Model name                                   |
| `LMS_API_KEY`        | `.env.docker.secret` | Backend API key for `query_api` auth         |
| `AGENT_API_BASE_URL` | Optional             | Backend API base URL (default: localhost:42002) |

> **Important**: The autochecker runs your agent with different credentials. Never hardcode API keys or URLs.

### Setup

1. Copy the example files:
   ```bash
   cp .env.agent.example .env.agent.secret
   cp .env.docker.example .env.docker.secret
   ```

2. Edit `.env.agent.secret` with your credentials:
   - `LLM_API_KEY`: Your API key from Qwen Code API or OpenRouter
   - `LLM_API_BASE`: The API endpoint URL
   - `LLM_MODEL`: The model name to use

3. Edit `.env.docker.secret` with backend credentials:
   - `LMS_API_KEY`: The backend API key (shared with docker-compose)

## Usage

### Run the agent

```bash
uv run agent.py "What does REST stand for?"
```

### Output

The agent outputs a single JSON object to stdout:

```json
{
  "answer": "Representational State Transfer.",
  "source": "wiki/rest-api.md#what-is-rest",
  "tool_calls": [
    {"tool": "list_files", "args": {"path": "wiki"}, "result": "rest-api.md\n..."},
    {"tool": "read_file", "args": {"path": "wiki/rest-api.md"}, "result": "..."}
  ]
}
```

- `answer`: The LLM's text response
- `source`: The wiki section that answers the question (format: `wiki/filename.md#section`)
- `tool_calls`: Array of all tool calls made during execution, each with:
  - `tool`: Tool name (`read_file` or `list_files`)
  - `args`: Arguments passed to the tool
  - `result`: The tool's return value

**Important**: Only valid JSON goes to stdout. All debug/log output goes to stderr.

## How It Works

### Task 1: Basic Flow

1. **Parse CLI argument**: The question is passed as the first command-line argument
2. **Load configuration**: Environment variables are loaded from `.env.agent.secret`
3. **Initialize OpenAI client**: The client is configured with `api_key` and `base_url`
4. **Send request**: POST to `<LLM_API_BASE>/v1/chat/completions` with the prompt
5. **Parse response**: Extract `choices[0].message.content` from the LLM response
6. **Format output**: Wrap answer in JSON with empty `tool_calls` array
7. **Print result**: Output JSON to stdout

### Task 2+: Agentic Loop

1. **Initialize messages**: System prompt + user question
2. **Call LLM with tools**: Send message with tool schemas attached
3. **Check response**:
   - If `tool_calls` present: execute each tool, append results, repeat from step 2
   - If text answer: extract answer + source, return JSON
4. **Max iterations**: Loop runs at most 10 times to prevent infinite loops
5. **Output**: JSON with answer, source, and all tool calls made

## Tools

The agent has access to three tools for navigating the project and querying the backend:

### `read_file`

Read the contents of a file from the project repository.

**Parameters:**
- `path` (string, required): Relative path from project root (e.g., `wiki/git-workflow.md`)

**Returns:**
- File contents as a string
- Error message if file doesn't exist or path is invalid

**Security:**
- Rejects paths containing `..` (directory traversal)
- Rejects absolute paths starting with `/`
- Validates resolved path is within project directory

**Example:**
```python
read_file("wiki/git-workflow.md")
# Returns: "# Git Workflow\n\n## Resolving Merge Conflicts\n..."
```

### `list_files`

List files and directories at a given path.

**Parameters:**
- `path` (string, required): Relative directory path from project root (e.g., `wiki`)

**Returns:**
- Newline-separated list of entries
- Directories are marked with trailing `/`
- Error message if directory doesn't exist or path is invalid

**Security:**
- Same path validation as `read_file`
- Skips hidden files (except `.qwen`) and `__pycache__`

**Example:**
```python
list_files("wiki")
# Returns: "git-workflow.md\nrest-api.md\nssh.md\n..."
```

### `query_api` (Task 3)

Query the backend API with authentication. Use for data-dependent questions like item counts, analytics, or testing endpoint behavior.

**Parameters:**
- `method` (string, required): HTTP method (GET, POST, PUT, DELETE)
- `path` (string, required): API path (e.g., `/items/`, `/analytics/completion-rate`)
- `body` (string, optional): JSON request body for POST/PUT requests

**Returns:**
- JSON string with `status_code` and `body`
- Error message if request fails or authentication is missing

**Authentication:**
- Uses `LMS_API_KEY` from `.env.docker.secret`
- Sends key as Bearer token in `Authorization` header
- Backend returns 401 if key is missing or invalid

**Example:**
```python
query_api("GET", "/items/")
# Returns: '{"status_code": 200, "body": "[...]"}'

query_api("GET", "/items/", "http://localhost:42002")
# Returns: '{"status_code": 401, "body": "{\"detail\": \"Invalid API key\"}"}'
```

**When to use:**
- Data counts: "How many items are in the database?"
- Live analytics: "What is the completion rate for lab-01?"
- Testing endpoints: "What status code does /items/ return without auth?"
- Debugging errors: Query an endpoint that crashes, then read source to diagnose

## System Prompt Strategy

The system prompt guides the LLM to:

1. **Use tools effectively**: 
   - Use `list_files` to discover wiki structure
   - Use `read_file` to read source code or documentation
   - Use `query_api` for data-dependent questions (counts, analytics, testing endpoints)
2. **Base answers on evidence**: Answer from actual file contents or API responses, not assumptions
3. **Include source references**: Format as `wiki/filename.md#section-anchor` (for wiki questions)
4. **Be concise**: Provide clear, direct answers

### Tool Selection Guide (Task 3)

The system prompt includes explicit guidance on tool selection:

```
Tool selection guide:
- For static questions about the codebase (framework, ports, structure), use read_file on source code
- For data-dependent questions (counts, scores, live data), use query_api
- For wiki/documentation questions, use list_files and read_file on wiki/
```

This helps the LLM decide between:
- **Wiki questions**: "What does the wiki say about SSH?" → `list_files` → `read_file`
- **System questions**: "What framework does the backend use?" → `read_file` on `backend/app/main.py`
- **Data questions**: "How many items are in the database?" → `query_api GET /items/`
- **Debugging questions**: "Why does /analytics/completion-rate crash?" → `query_api` → `read_file` on error location

Example system prompt excerpt:
```
You are a documentation assistant for a software engineering lab.
You have access to tools to read files, list directories, and query the backend API.

When answering questions:
1. Use list_files to discover what files exist in a directory
2. Use read_file to read source code or documentation files
3. Use query_api to query the running backend API for:
   - Data counts (e.g., "how many items")
   - Live analytics (e.g., completion rates, top learners)
   - Testing endpoint behavior (e.g., status codes, error responses)
   - Debugging API errors
```

## Error Handling

- **Missing environment variables**: Raises `ValueError` with helpful message
- **LLM API errors**: Caught and returned in the JSON `answer` field, exit code 1
- **No CLI argument**: Prints usage to stderr, exit code 1

## Testing

Run the regression test:

```bash
uv run pytest backend/tests/unit/test_agent.py -v
```

The test:
1. Runs `agent.py` as a subprocess
2. Parses the JSON output
3. Verifies `answer` and `tool_calls` fields are present

## Development

### Dependencies

- `openai`: OpenAI Python SDK (supports OpenAI-compatible APIs)
- `python-dotenv`: Load environment variables from `.env` files

### Add new features

In Task 2, you will:
- Add tools (file system, API queries, etc.)
- Implement the agentic loop
- Populate `tool_calls` with tool invocations

In Task 3, you will:
- Add domain knowledge (wiki articles)
- Expand the system prompt
- Improve tool selection

## Troubleshooting

### "LLM_API_KEY not found"

Make sure `.env.agent.secret` exists and contains `LLM_API_KEY=...`

### Connection refused

Check that `LLM_API_BASE` points to a running API endpoint. For Qwen Code API on your VM, ensure the proxy is running:

```bash
# On your VM, in ~/qwen-code-oai-proxy
docker compose ps
```

### 401 Unauthorized

Your `LLM_API_KEY` is incorrect or expired.

### Rate limit errors

Free-tier models have daily limits. Wait 24 hours or switch to a different provider.

## Lessons Learned (Task 3)

### Architecture Decisions

1. **Two environment files**: Separating LLM credentials (`.env.agent.secret`) from backend API credentials (`.env.docker.secret`) keeps concerns isolated and matches the Docker compose setup.

2. **Bearer token authentication**: The backend uses `Authorization: Bearer <API_KEY>` header format, which is standard for REST APIs and works with FastAPI's `HTTPBearer` security.

3. **httpx over requests**: Using `httpx` instead of `requests` provides better async support for future enhancements and is more modern.

4. **Tool description matters**: The LLM relies heavily on tool descriptions to decide which tool to use. Being explicit about when to use `query_api` vs `read_file` significantly improves tool selection accuracy.

### Benchmark Iteration Strategy

The key to passing the benchmark is systematic iteration:

1. **Run eval and stop at first failure**: `run_eval.py` stops at the first failure, making it easy to focus on one issue at a time.

2. **Check tool usage first**: If the wrong tool was called, improve the tool description or system prompt guidance.

3. **Check answer content**: If the right tool was called but the answer is wrong, check:
   - Did the API return an error?
   - Did the LLM misinterpret the response?
   - Is the answer missing key keywords?

4. **Common fixes**:
   - **Division by zero bug**: The `/analytics/completion-rate` endpoint crashes when no learners exist. The agent needs to query the endpoint, see the error, then read `backend/app/routers/analytics.py` to find the bug.
   - **Top learners bug**: The `/analytics/top-learners` endpoint can fail if data is None. The agent needs to trace the error to the source code.
   - **Request lifecycle question**: This requires reading both `docker-compose.yml` and `backend/app/main.py` to trace the full request path.

### Key Insights

- **Tool chaining is essential**: Complex questions require multiple tool calls. For example, debugging an API error requires `query_api` first, then `read_file` on the source code.

- **Source is optional for system questions**: Questions about the running system (framework, ports, status codes) don't have wiki sources. The `source` field is correctly left empty for these.

- **Environment variable flexibility**: Reading all config from environment variables (not hardcoded) is critical for the autochecker to inject its own credentials.

### Final Eval Score

*To be filled after running the benchmark with proper LLM credentials.*

The agent is designed to pass all 10 local questions and the additional hidden questions from the autochecker. The key is having a genuinely working agent that can:
- Select the right tool for each question type
- Chain tools for multi-step debugging
- Handle API errors gracefully
- Extract relevant information from source code
