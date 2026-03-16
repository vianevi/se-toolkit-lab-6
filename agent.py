#!/usr/bin/env python3
"""
Agent module for interacting with LLM.

Usage:
    uv run agent.py "Your question here"

Output:
    JSON to stdout: {"answer": "...", "tool_calls": []}
    Debug logs go to stderr.
"""

import os
import sys
import json
from dotenv import load_dotenv
from openai import OpenAI


class Agent:
    """A simple agent that calls an LLM and returns structured JSON responses."""

    def __init__(self):
        """
        Initialize the agent with configuration from environment variables.

        Reads from .env.agent.secret:
            - LLM_API_KEY: API key for authentication
            - LLM_API_BASE: Base URL for the LLM API (OpenAI-compatible)
            - LLM_MODEL: Model name to use
        """
        # Load environment variables from .env.agent.secret
        load_dotenv(".env.agent.secret")

        # Get configuration from environment
        api_key = os.getenv("LLM_API_KEY")
        api_base = os.getenv("LLM_API_BASE")
        model = os.getenv("LLM_MODEL")

        # Validate required configuration
        if not api_key:
            raise ValueError(
                "LLM_API_KEY not found. Please set it in .env.agent.secret file."
            )
        if not api_base:
            raise ValueError(
                "LLM_API_BASE not found. Please set it in .env.agent.secret file."
            )
        if not model:
            raise ValueError(
                "LLM_MODEL not found. Please set it in .env.agent.secret file."
            )

        # Store configuration
        self.api_key = api_key
        self.api_base = api_base
        self.model = model

        # Initialize OpenAI client with custom base URL
        # This allows using any OpenAI-compatible API (Qwen Code API, OpenRouter, etc.)
        self.client = OpenAI(api_key=self.api_key, base_url=self.api_base)

        print(f"Agent initialized with model: {self.model}", file=sys.stderr)

    def call_llm(self, prompt: str) -> str:
        """
        Call the LLM with the given prompt and return the answer.

        Args:
            prompt: The user question/prompt to send to the LLM

        Returns:
            The LLM's text response

        Raises:
            Exception: If the LLM API call fails
        """
        print(f"Sending prompt to LLM: {prompt[:50]}...", file=sys.stderr)

        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
            temperature=0.7,
            max_tokens=500,
        )

        answer = response.choices[0].message.content or ""
        print(f"Received answer from LLM", file=sys.stderr)

        return answer

    def format_response(self, answer: str) -> str:
        """
        Format the response as JSON with answer and tool_calls fields.

        Args:
            answer: The LLM's text answer

        Returns:
            JSON string with answer and empty tool_calls array
        """
        response: dict[str, str | list[dict]] = {  # type: ignore[unknown-variable-type]
            "answer": answer,
            "tool_calls": [],  # Empty for now, will be populated in Task 2
        }
        return json.dumps(response, ensure_ascii=False)


def main():
    """Main entry point for the agent CLI."""
    # Get prompt from command line arguments
    if len(sys.argv) < 2:
        print("Error: Please provide a prompt", file=sys.stderr)
        print('Usage: uv run agent.py "your prompt here"', file=sys.stderr)
        sys.exit(1)

    prompt = sys.argv[1]

    try:
        # Create agent and call LLM
        agent = Agent()
        answer = agent.call_llm(prompt)
        formatted_response = agent.format_response(answer)

        # Output JSON to stdout (only valid JSON, no debug info)
        print(formatted_response)

        sys.exit(0)

    except Exception as e:
        # Log error to stderr
        print(f"Error: {str(e)}", file=sys.stderr)

        # Still output valid JSON structure for consistency
        error_response: dict[str, str | list[dict]] = {  # type: ignore[unknown-variable-type]
            "answer": f"Error: {str(e)}",
            "tool_calls": [],
        }
        print(json.dumps(error_response))
        sys.exit(1)


if __name__ == "__main__":
    main()
