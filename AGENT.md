# Lab Agent

A CLI tool that connects to an LLM and answers questions. This is the foundation for the agentic system you will build across Tasks 1–3.

## Architecture

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

The agent reads configuration from `.env.agent.secret` (gitignored):

```bash
# LLM API key
LLM_API_KEY=your-api-key-here

# API base URL (OpenAI-compatible endpoint)
LLM_API_BASE=http://<vm-ip>:<port>/v1

# Model name
LLM_MODEL=qwen3-coder-plus
```

### Setup

1. Copy the example file:
   ```bash
   cp .env.agent.example .env.agent.secret
   ```

2. Edit `.env.agent.secret` with your credentials:
   - `LLM_API_KEY`: Your API key from Qwen Code API or OpenRouter
   - `LLM_API_BASE`: The API endpoint URL
   - `LLM_MODEL`: The model name to use

## Usage

### Run the agent

```bash
uv run agent.py "What does REST stand for?"
```

### Output

The agent outputs a single JSON line to stdout:

```json
{"answer": "Representational State Transfer.", "tool_calls": []}
```

- `answer`: The LLM's text response
- `tool_calls`: Empty array (will be populated in Task 2 when tools are added)

**Important**: Only valid JSON goes to stdout. All debug/log output goes to stderr.

## How It Works

1. **Parse CLI argument**: The question is passed as the first command-line argument
2. **Load configuration**: Environment variables are loaded from `.env.agent.secret`
3. **Initialize OpenAI client**: The client is configured with `api_key` and `base_url`
4. **Send request**: POST to `<LLM_API_BASE>/v1/chat/completions` with the prompt
5. **Parse response**: Extract `choices[0].message.content` from the LLM response
6. **Format output**: Wrap answer in JSON with empty `tool_calls` array
7. **Print result**: Output JSON to stdout

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
