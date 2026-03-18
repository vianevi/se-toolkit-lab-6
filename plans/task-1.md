# Task 1: Call an LLM from Code

## LLM Provider and Model

- **Provider**: Qwen Code API (OpenAI-compatible endpoint)
- **Model**: `qwen3-coder-plus`
- **Why**: 1000 free requests/day, works from Russia, no credit card required

## Environment Configuration

The agent reads configuration from `.env.agent.secret`:

```
LLM_API_KEY=<api-key>
LLM_API_BASE=http://<vm-ip>:<port>/v1
LLM_MODEL=qwen3-coder-plus
```

## Agent Structure

```
agent.py
├── Agent class
│   ├── __init__: Load env vars, create OpenAI client with base_url
│   ├── call_llm(prompt): Send message to LLM, return answer
│   └── format_response(answer): Return JSON {answer, tool_calls}
└── main(): Parse CLI arg, call agent, print JSON to stdout
```

## Data Flow

1. User runs: `uv run agent.py "What is REST?"`
2. `main()` gets prompt from `sys.argv[1]`
3. `Agent` loads env vars from `.env.agent.secret`
4. `Agent.call_llm()` sends POST to `LLM_API_BASE/v1/chat/completions`
5. LLM returns response, extract `choices[0].message.content`
6. `format_response()` wraps answer in JSON with empty `tool_calls`
7. Print JSON to stdout, debug logs to stderr

## Error Handling

- Missing env vars → raise ValueError with helpful message
- LLM API error → catch exception, return error in JSON, exit 1
- No CLI argument → print usage to stderr, exit 1

## Testing

- 1 regression test: run agent.py as subprocess, parse JSON, check fields
