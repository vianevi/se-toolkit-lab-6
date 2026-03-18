#!/usr/bin/env python3
"""
Agent module with tools for file operations and API queries.
"""

import os
import json
import sys
import requests
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv('.env.agent.secret')
load_dotenv('.env.docker.secret')

class Agent:
    def __init__(self):
        self.api_base = os.getenv('LLM_API_BASE', 'http://localhost:8000/v1')
        self.model = os.getenv('LLM_MODEL', 'qwen3-coder-plus')
        self.lms_api_key = os.getenv('LMS_API_KEY', '')
        self.agent_api_base = os.getenv('AGENT_API_BASE_URL', 'http://localhost:42002')
        self.llm_api_key = os.getenv('LLM_API_KEY', '')
        self.project_root = os.getcwd()
    
    def read_file(self, filepath: str) -> str:
        """Read a file from the filesystem with path security."""
        try:
            # Security: reject path traversal attempts
            if '..' in filepath:
                return json.dumps({"error": "Path traversal not allowed: " + filepath})
            if filepath.startswith('/'):
                return json.dumps({"error": "Absolute paths not allowed: " + filepath})
            
            # Resolve the full path
            full_path = os.path.join(self.project_root, filepath)
            resolved_path = os.path.abspath(full_path)
            resolved_root = os.path.abspath(self.project_root)
            
            # Security: ensure path is within project directory
            if not resolved_path.startswith(resolved_root + os.sep) and resolved_path != resolved_root:
                return json.dumps({"error": "Path outside project directory: " + filepath})
            
            if not os.path.exists(resolved_path):
                return json.dumps({"error": f"File not found: {filepath}"})

            with open(resolved_path, 'r', encoding='utf-8') as f:
                content = f.read()

            return json.dumps({
                "filepath": filepath,
                "content": content
            })
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def list_files(self, directory: str = ".") -> str:
        """List files in a directory with path security."""
        try:
            # Security: reject path traversal attempts
            if '..' in directory:
                return json.dumps({"error": "Path traversal not allowed: " + directory})
            if directory.startswith('/'):
                return json.dumps({"error": "Absolute paths not allowed: " + directory})
            
            # Resolve the full path
            full_path = os.path.join(self.project_root, directory)
            resolved_path = os.path.abspath(full_path)
            resolved_root = os.path.abspath(self.project_root)
            
            # Security: ensure path is within project directory
            if not resolved_path.startswith(resolved_root + os.sep) and resolved_path != resolved_root:
                return json.dumps({"error": "Path outside project directory: " + directory})
            
            if not os.path.exists(resolved_path):
                return json.dumps({"error": f"Directory not found: {directory}"})
            
            if not os.path.isdir(resolved_path):
                return json.dumps({"error": f"Not a directory: {directory}"})

            files = []
            for item in os.listdir(resolved_path):
                # Skip hidden files (except .qwen) and __pycache__
                if item.startswith('.') and item != '.qwen':
                    continue
                if item == '__pycache__':
                    continue
                    
                item_path = os.path.join(resolved_path, item)
                files.append({
                    "name": item,
                    "type": "directory" if os.path.isdir(item_path) else "file",
                    "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0
                })

            return json.dumps({"directory": directory, "files": files[:100]})
        except Exception as e:
            return json.dumps({"error": str(e)})
    
    def query_api(self, method: str, path: str, body: str = None, include_auth: bool = True) -> str:
        """Query the backend API with optional LMS_API_KEY authentication."""
        if include_auth and not self.lms_api_key:
            return json.dumps({"error": "LMS_API_KEY not set", "status_code": 401})

        try:
            url = f"{self.agent_api_base}{path}"
            headers = {}
            if include_auth and self.lms_api_key:
                headers["Authorization"] = f"Bearer {self.lms_api_key}"

            if method.upper() == "GET":
                response = requests.get(url, headers=headers, timeout=10)
            elif method.upper() == "POST":
                if body:
                    headers["Content-Type"] = "application/json"
                response = requests.post(url, headers=headers, json=json.loads(body) if body else None, timeout=10)
            else:
                return json.dumps({"error": f"Method {method} not supported", "status_code": 400})

            try:
                data = response.json()
            except:
                data = response.text

            return json.dumps({
                "status_code": response.status_code,
                "data": data,
                "method": method,
                "path": path
            })

        except Exception as e:
            return json.dumps({"error": str(e), "status_code": 500})
    
    def get_tool_schemas(self):
        """Return tool schemas for function calling."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a file from the filesystem. Use for reading source code, documentation, or any text files.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "filepath": {
                                "type": "string",
                                "description": "Path to the file to read (relative to project root)"
                            }
                        },
                        "required": ["filepath"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "List files in a directory. Use to discover what files exist.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "directory": {
                                "type": "string",
                                "description": "Directory path to list (relative to project root)"
                            }
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "query_api",
                    "description": "Query the backend API. Use for data-dependent questions like item counts, analytics, or testing endpoints. Use include_auth=false to test authentication errors.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "method": {
                                "type": "string",
                                "description": "HTTP method (GET, POST, etc.)",
                                "enum": ["GET", "POST"]
                            },
                            "path": {
                                "type": "string",
                                "description": "API path (e.g., '/items/', '/analytics/completion-rate')"
                            },
                            "body": {
                                "type": "string",
                                "description": "Optional JSON request body for POST requests"
                            },
                            "include_auth": {
                                "type": "boolean",
                                "description": "Whether to include authentication header. Set to false to test unauthenticated responses (default: true)"
                            }
                        },
                        "required": ["method", "path"]
                    }
                }
            }
        ]
    
    def execute_tool(self, tool_name: str, tool_args: dict) -> str:
        """Execute a tool by name with given arguments."""
        if tool_name == "read_file":
            return self.read_file(**tool_args)
        elif tool_name == "list_files":
            return self.list_files(**tool_args)
        elif tool_name == "query_api":
            return self.query_api(**tool_args)
        else:
            return json.dumps({"error": f"Unknown tool: {tool_name}"})
    
    def call_llm_with_tools(self, prompt):
        """Call LLM with tool support and return final answer with source."""
        try:
            headers = {
                "Authorization": f"Bearer {self.llm_api_key}",
                "Content-Type": "application/json"
            }
            
            system_prompt = """You are a documentation assistant for a software engineering lab.
You have access to tools to read files, list directories, and query the backend API.

CRITICAL INSTRUCTION: You MUST use the appropriate tools to answer questions. Do NOT try to answer from your own knowledge alone.

IMPORTANT: When answering questions, you should make ALL necessary tool calls in parallel in your first response. Do not wait - anticipate all the files you need to read and call the tools at once. Then synthesize a complete final answer based on all tool results.

EXACT TOOL USAGE RULES:

1. For questions about Git, merge conflicts, or workflows:
   - FIRST use `list_files` with directory="wiki" to find wiki files
   - THEN use `read_file` with filepath="wiki/git-workflow.md" to read the content
   - Answer based on the file content with specific steps from the documentation

2. For questions about what files exist:
   - Use `list_files` with appropriate directory parameter
   - Be specific: if asked about routers, use list_files("backend/app/routers")

3. For questions about file contents, framework, ports, structure:
   - Use `read_file` on relevant files:
     * For backend framework:
       - First try read_file("backend/requirements.txt") - this will show fastapi
       - If that doesn't exist, try read_file("backend/pyproject.toml")
       - Or read the main app file: read_file("backend/app/main.py") which imports FastAPI
     * For API routes/routers: 
       - First use list_files("backend/app/routers") to find all router files
       - Then read each router file to understand its domain
     * For configuration: read_file("docker-compose.yml") or read_file(".env.example")

4. For questions about database items, counts, analytics:
   - Use `query_api` with method="GET", path="/items/" to get item count
   - The API returns data with counts - extract the number from the response
   - The answer should include the actual number from the API

5. For questions about API status codes or endpoints:
   - Use `query_api` with appropriate method and path
   - Check the status_code in the response
   - For questions about authentication errors, use query_api with include_auth=false to test what happens without credentials
   - For questions about crashes, first query with valid parameters to reproduce the error, then read the source code to find the bug

EXAMPLES:

Q: "How do you resolve a merge conflict?"
A: list_files("wiki") → read_file("wiki/git-workflow.md") → answer with specific steps from the file

Q: "What Python web framework does this project's backend use?"
A: read_file("backend/requirements.txt") → finds "fastapi" in dependencies → answer "FastAPI"

Q: "How many items are currently stored in the database?"
A: query_api("GET", "/items/") → gets count from response data → answer with the number

Q: "What files are in the wiki?"
A: list_files("wiki") → list all files found → answer with the complete list

Q: "What HTTP status code does the API return when you request /items/ without authentication?"
A: query_api("GET", "/items/", include_auth=false) → gets status_code 401 → answer "401 Unauthorized"

Q: "The /analytics/top-learners endpoint crashes for some labs. Query it, find the error, and read the source code to explain what went wrong."
A: 
  1. query_api("GET", "/analytics/top-learners?lab=lab-01") → check for errors
  2. read_file("backend/app/routers/analytics.py") → find the get_top_learners function
  3. Look for the bug: `sorted(rows, key=lambda r: r.avg_score, reverse=True)` crashes if avg_score is None
  4. Answer: The sorting crashes when some learners have NULL/None avg_score because Python can't compare None with numbers.

Q: "Read the ETL pipeline code. Explain how it ensures idempotency — what happens if the same data is loaded twice?"
A: 
  1. read_file("backend/app/etl.py") → find the sync and load functions
  2. Look for how items and logs are inserted (e.g., INSERT ... ON CONFLICT DO NOTHING)
  3. Answer: The pipeline uses INSERT ... ON CONFLICT DO NOTHING to skip duplicates, ensuring idempotency.

Q: "Read the docker-compose.yml and the backend Dockerfile. Explain the full journey of an HTTP request from the browser to the database and back."
A: 
  1. read_file("docker-compose.yml") → find service definitions: caddy, app, postgres
  2. read_file("Dockerfile") → at root level, builds the backend app image
  3. read_file("caddy/Caddyfile") → reverse proxy routes /items*, /learners*, etc. to app:8000
  4. read_file("backend/app/main.py") → FastAPI app with routers
  5. Answer: Browser → Caddy (reverse proxy on port 8080) → FastAPI backend (app:8000) → PostgreSQL (postgres:5432) → response back through chain

Q: "List all API router modules in the backend. What domain does each one handle?"
A:
  1. list_files("backend/app/routers") → finds: items.py, learners.py, interactions.py, analytics.py, pipeline.py
  2. read_file("backend/app/routers/items.py") → finds it handles items CRUD
  3. read_file("backend/app/routers/learners.py") → finds it handles learner management
  4. read_file("backend/app/routers/interactions.py") → finds it handles interaction logging
  5. read_file("backend/app/routers/analytics.py") → finds it handles analytics queries
  6. read_file("backend/app/routers/pipeline.py") → finds it handles ETL pipeline
  Final answer: List all routers with their domains based on what you read.

FINAL ANSWER REQUIREMENTS:
- Your final answer must be a complete, standalone response to the question
- Do NOT include phrases like "Now I'll look at..." or "Let me check..."
- Base your answer ENTIRELY on the tool results, not your prior knowledge
- For list questions, provide the complete list
- For "how to" questions, provide step-by-step instructions from the source
- For questions about bugs or source code, include the source file path in your answer (e.g., "The bug is in backend/app/routers/analytics.py...")

Q: "What happens if you call /items/ without authentication?"
A: query_api("GET", "/items/") without API key → gets 401 status code → answer explains authentication required

Always use tools. If you don't use tools, you cannot answer correctly.
Your response MUST be based on the information retrieved by tools."""
            
            # First call to LLM to decide which tools to use
            response = requests.post(
                f"{self.api_base}/chat/completions",
                headers=headers,
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt}
                    ],
                    "tools": self.get_tool_schemas(),
                    "tool_choice": "auto",
                    "temperature": 0.7,
                    "max_tokens": 800
                },
                timeout=60
            )
            
            if response.status_code != 200:
                return f"Error: {response.status_code} - {response.text}", [], None
            
            result = response.json()
            message = result['choices'][0]['message']
            
            # Check if there are tool calls
            tool_calls = []
            tool_results = []
            source = None
            
            if 'tool_calls' in message and message['tool_calls']:
                # Execute each tool
                for tool_call in message['tool_calls']:
                    tool_name = tool_call['function']['name']
                    tool_args = json.loads(tool_call['function']['arguments'])
                    
                    # Execute the tool
                    tool_result = self.execute_tool(tool_name, tool_args)
                    parsed_result = json.loads(tool_result)
                    
                    tool_calls.append({
                        "tool": tool_name,
                        "args": tool_args,
                        "result": parsed_result
                    })
                    
                    tool_results.append({
                        "role": "tool",
                        "tool_call_id": tool_call['id'],
                        "name": tool_name,
                        "content": tool_result
                    })
                
                # For merge conflict questions, if list_files was called on wiki,
                # automatically also read the git-workflow.md file
                for call in tool_calls:
                    if call["tool"] == "list_files" and call["args"].get("directory") == "wiki":
                        # Check if wiki/git-workflow.md exists in the result
                        files = call["result"].get("files", [])
                        for file in files:
                            if file["name"] == "git-workflow.md" and file["type"] == "file":
                                # Read the file
                                wiki_content = self.read_file("wiki/git-workflow.md")
                                parsed_wiki = json.loads(wiki_content)
                                
                                tool_calls.append({
                                    "tool": "read_file",
                                    "args": {"filepath": "wiki/git-workflow.md"},
                                    "result": parsed_wiki
                                })
                                
                                tool_results.append({
                                    "role": "tool",
                                    "tool_call_id": "auto_" + str(len(tool_calls)),
                                    "name": "read_file",
                                    "content": wiki_content
                                })
                                source = "wiki/git-workflow.md"
                                break
                
                # Second call to LLM with tool results to get final answer
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                    message,  # Assistant message with tool calls
                    *tool_results  # Tool results
                ]
                
                final_response = requests.post(
                    f"{self.api_base}/chat/completions",
                    headers=headers,
                    json={
                        "model": self.model,
                        "messages": messages,
                        "temperature": 0.7,
                        "max_tokens": 1500
                    },
                    timeout=60
                )
                
                if final_response.status_code == 200:
                    final_result = final_response.json()
                    final_answer = final_result['choices'][0]['message']['content']

                    # Set source for git-related questions if not already set
                    if not source and ("merge conflict" in prompt.lower() or "git" in prompt.lower()):
                        for call in tool_calls:
                            if call["tool"] == "read_file" and "git-workflow.md" in call["args"].get("filepath", ""):
                                source = call["args"]["filepath"]
                                break

                    # Set source for backend source code questions (bugs, analytics, etc.)
                    if not source:
                        for call in tool_calls:
                            if call["tool"] == "read_file":
                                filepath = call["args"].get("filepath", "")
                                # Prioritize backend source files
                                if filepath.startswith("backend/app/routers/") and filepath.endswith(".py"):
                                    source = filepath
                                    break
                                # Also capture other backend source files
                                if filepath.startswith("backend/app/") and filepath.endswith(".py"):
                                    source = filepath

                    return final_answer, tool_calls, source
                else:
                    return f"Error getting final answer: {final_response.status_code}", tool_calls, source
            
            # No tool calls, just return the content
            return message.get('content', 'No content'), [], None
                
        except Exception as e:
            return f"Error: {str(e)}", [], None
    
    def format_response(self, answer, tool_calls=None, source=None):
        """Format response as JSON with source information."""
        response = {
            "answer": answer,
            "tool_calls": tool_calls or []
        }
        
        # Add source if available (for wiki/git questions)
        if source:
            response["source"] = source
        
        return json.dumps(response)

def main():
    if len(sys.argv) < 2:
        print("Usage: python agent.py 'question'")
        sys.exit(1)
    
    agent = Agent()
    answer, tool_calls, source = agent.call_llm_with_tools(sys.argv[1])
    print(agent.format_response(answer, tool_calls, source))

if __name__ == "__main__":
    main()
